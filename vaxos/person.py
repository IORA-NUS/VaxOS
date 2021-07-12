from random import shuffle, random, choice
import math
import numpy as np
from vaxos.params import location_types, vaccine_types

class Person:
    ''' '''

    # d_type = '7'

    params = {}
    # vc_pref = []
    loc_pref = []
    loc_rank = {}
    day_pref = []
    booking_time = 0 # generated via an exponential dist
    utility = []
    appt_time = 0

    def __init__(self, params, booking_time, appt_time=0, arrival_duration=45):
        ''' '''
        self.params = params
        location_type_pref = location_types
        vaccine_type_pref = vaccine_types
        self.appt_time = appt_time
        self.arrival_duration = arrival_duration

        if params['utility']['vaccine_bias']['vaccine'] == 'random':
            for vac in vaccine_type_pref:
                for loc in location_type_pref:
                    if self.params['vaccine_settings'][vac]['location'].get(loc) is not None:
                        tmp_pref = [f"{loc}_{vac}_{loc_id:02d}" for loc_id in list(range(self.params['vaccine_settings'][vac]['location'][loc][booking_time]))]
                        shuffle(tmp_pref)
                        # self.loc_pref = self.loc_pref + tmp_pref
                        num_pref_locations = None
                        try:
                            num_pref_locations = params['utility']['limit_location_preference'][loc]
                            if num_pref_locations is None or num_pref_locations > len(tmp_pref):
                                raise Exception("Unacceptable limit_location_preference")
                        except Exception as e:
                            num_pref_locations = len(tmp_pref)

                        self.loc_pref = self.loc_pref + tmp_pref[:num_pref_locations]
        else:
            # for vac in vaccine_type_pref:
            #     # if vac != params['utility']['vaccine_bias']['vaccine']: # Should be vaccine name
            #     #     if random() <= params['utility']['vaccine_bias']['bias']:
            #     #         # % of population will never choose alternate vaccine
            #     #         continue
            choose = random()
            if choose <= params['utility']['vaccine_bias']['bias']:
                vac = params['utility']['vaccine_bias']['vaccine']
            else:
                alternate_vac = [v for v in vaccine_types if v != params['utility']['vaccine_bias']['vaccine']]
                # alternate_vac.remove(params['utility']['vaccine_bias']['vaccine'])
                vac = choice(alternate_vac)

            for loc in location_type_pref:
                if self.params['vaccine_settings'][vac]['location'].get(loc) is not None:
                    tmp_pref = [f"{loc}_{vac}_{loc_id:02d}" for loc_id in list(range(self.params['vaccine_settings'][vac]['location'][loc][booking_time]))]
                    shuffle(tmp_pref)
                    # self.loc_pref = self.loc_pref + tmp_pref
                    num_pref_locations = None
                    try:
                        num_pref_locations = params['utility']['limit_location_preference'][loc]
                        if num_pref_locations is None or num_pref_locations > len(tmp_pref):
                            raise Exception("Unacceptable limit_location_preference")
                    except Exception as e:
                        num_pref_locations = len(tmp_pref)

                    self.loc_pref = self.loc_pref + tmp_pref[:num_pref_locations]

        # if d_type in ['7']:
        #     shuffle(self.loc_pref)
        shuffle(self.loc_pref)

        for i in range(len(self.loc_pref)):
            self.loc_rank[self.loc_pref[i]] = i + 1

        # print(self.loc_rank)

        self.day_pref = list(range(7))
        shuffle(self.day_pref)

        self.booking_time = booking_time

        # self.d_type = d_type
        self.d_type = 'DEPRECATED'


    def generate_utility(self):
        ''' '''
        # limit_time_preference = self.params['duration']
        # try:
        #     limit_time_preference = self.params['utility']['limit_time_preference']
        # except: pass
        limit_time_preference = self.params['utility']['limit_time_preference']
        invitation_frequency = self.params['invitation_frequency']

        # person_utility = [-math.inf] * len(self.loc_pref) * (min(self.appt_time + limit_time_preference + invitation_frequency,  self.params['duration']) - self.booking_time)
        # person_utility_index = [-math.inf] * len(self.loc_pref) * (min(self.appt_time + limit_time_preference + invitation_frequency,  self.params['duration']) - self.booking_time)
        person_utility = [-math.inf] * len(self.loc_pref) * (min(self.appt_time + self.arrival_duration,  self.params['duration']) - self.booking_time)
        person_utility_index = [-math.inf] * len(self.loc_pref) * (min(self.appt_time + self.arrival_duration,  self.params['duration']) - self.booking_time)

        loc_rank = 0
        idx = 0
        for loc_id in self.loc_pref:
            # if self.booking_time <= min(self.appt_time + limit_time_preference + invitation_frequency,  self.params['duration']):
            #     for period in range(self.booking_time, min(self.appt_time + limit_time_preference + invitation_frequency,  self.params['duration'])):
            if self.booking_time <= min(self.appt_time + self.arrival_duration,  self.params['duration']):
                for period in range(self.booking_time, min(self.appt_time + self.arrival_duration,  self.params['duration'])):
                    period_rank = self.day_pref.index((period-self.booking_time) % 7)
                    # person_utility.append(
                    person_utility[idx] = \
                        (self.params['utility']['location'] * ((len(self.loc_pref) - loc_rank) / len(self.loc_pref))) + \
                        (self.params['utility']['time'] * (
                            self.params['utility']['day_of_week'] * (period_rank / 7) - \
                            1 * ((period-self.booking_time) / 7)
                        )) + \
                        (random()/100)
                        # (self.params['utility']['location'] * ((len(self.loc_pref) - loc_rank) / len(self.loc_pref))) + \
                        # (self.params['utility']['time'] * (
                        #     1 * (period_rank / 7) - \
                        #     1 * math.ceil(period / 7)
                        # )) + \
                        # (random()/100)
                    # )
                    # person_utility_index.append((loc_id, period))
                    person_utility_index[idx] = (loc_id, period)
                    idx += 1
                loc_rank += 1

        sorted_utility = np.argsort(person_utility)[::-1]
        return person_utility_index, sorted_utility

    # def get_vc_rank(self, vc_id):
    #     return self.vc_pref.index(vc_id) + 1

    def get_loc_rank(self, loc_id):
        # return self.loc_pref.index(loc_id) + 1
        return self.loc_rank[loc_id]
