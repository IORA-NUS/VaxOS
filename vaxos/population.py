import math
import numpy as np
import pandas as pd
from numpy.random import normal

# from custom_dist import custom_dist
from vaxos.params import Params, vaccine_types
from vaxos.person import Person
from vaxos.custom_dist import CustomDist

class Population:
    ''' '''

    def __init__(self, params):
        ''' '''
        self.params = params
        self.demand = []
        self.invitations = None
        self.invited_demand = {}
        self.demand_spillover = 0
        self.invitation_freq = params['invitation_frequency']

        self.distribution = CustomDist(params['distribution'])

        # print(params['demand_generator'])
        if params['demand_generator'] == 'Target':
            # self.demand, self.demand_spillover, self.invited_demand, self.invitations = self.get_demand_from_target(params)
            _, _, _, self.invitations = self.get_demand_from_target(params)
            # print(len(self.invitations))

            params['invitation'] = ((np.array(self.invitations) / (params['scale_factor'] * params['response_rate'])).astype(int)).tolist()
            self.invitations = ((np.array(self.invitations) / params['response_rate']).astype(int)).tolist()
            # print(self.invitations)

        # print(len(self.invitations))

        # elif params['demand_generator'] == 'Invited':
        if self.invitations is None:
            self.invitations =  (np.array(params['invitation']) * params['scale_factor']).tolist()

        self.invitations  = self.invitations + ([0] * (params['duration'] - len(self.invitations)))
        # print(len(self.invitations))


        self.demand, self.demand_spillover, self.invited_demand = self.adjusted_demand(self.invitations, params['distribution'], params['response_rate'])
        # print(len(self.demand))

        for vac in vaccine_types:
            known_appts, _, _ = Params.get_appt_book(params, vac, mode='Simulation')
            self.demand = np.add(self.demand, np.array(known_appts[0:params['duration']])*params['scale_factor'])

        self.demand = self.demand.tolist()

        self.arrival = [0] * params['duration']


        # print(self.demand)
        self.time = 0

    def get_demand_from_target(self, params):
        ''' '''
        invitations = [0] * params['duration']
        demand = np.array([0] * params['duration'])
        for vac in vaccine_types:
            known_appts, _, _ = Params.get_appt_book(params, vac, mode='Simulation')
            demand = np.add(demand, known_appts[0:params['duration']])

        demand = (demand * params['scale_factor']).astype(int)

        # print(demand)
        # # target = (np.array(params['target']) * params['scale_factor']) #.astype(int)
        target = [0]*params['duration']
        for vac in vaccine_types:
            target = np.add(target, (np.array(params['vaccine_settings'][vac]['target'][0:params['duration']]) * params['scale_factor'])) #.astype(int)

        # print(target.tolist())

        # distribution = params['distribution']
        demand_spillover = 0
        invited_demand = {}

        for wave in range(0, params['duration'], self.invitation_freq):
            start = wave
            end = min(wave + self.invitation_freq, params['duration'])
            # print(start, end, target[wave])
            total_known_arrival = sum(demand[start:end])


            if wave == 0:
                invited_demand[wave] = demand.tolist()
                # print('updating invited_demand')
            else:
                invited_demand[wave] = [0]*params['duration']

            # target = total_known_arrival + 30% deficit

            # target_deficit = max(0, (target[wave] - total_known_arrival) / sum(custom_dist[f"{distribution}_mean"][0:self.invitation_freq]))

            # for i in range(len(custom_dist[f"{distribution}_mean"])):
            #     invitations[wave] += int(custom_dist[f"{distribution}_mean"][i] * target_deficit)

            #     if start+i < params['duration']:
            #         demand[start+i] += int(custom_dist[f"{distribution}_mean"][i] * target_deficit)
            #         invited_demand[wave][start+i] += int(custom_dist[f"{distribution}_mean"][i] * target_deficit)
            #     else:
            #         demand_spillover += int(custom_dist[f"{distribution}_mean"][i] * target_deficit)

            target_deficit = max(0, (target[wave] - total_known_arrival) / sum(self.distribution.mean()[0:self.invitation_freq]))

            for i in range(len(self.distribution.mean())):
                invitations[wave] += int(self.distribution.mean()[i] * target_deficit)

                if start+i < params['duration']:
                    demand[start+i] += int(self.distribution.mean()[i] * target_deficit)
                    invited_demand[wave][start+i] += int(self.distribution.mean()[i] * target_deficit)
                else:
                    demand_spillover += int(self.distribution.mean()[i] * target_deficit)

            # print('invited_demand: ', wave, invited_demand)

        return demand, demand_spillover, invited_demand, invitations

    def adjusted_demand(self, invitation, distribution='poisson', response_rate=1):
        ''' Apply booking request distribution
        - Demand recieved at period 't' will be adjusted based on a possion arrival with peak at day t+4
        '''
        new_demand = [0] * len(invitation)
        demand_spillover = 0
        invited_demand = {}

        if distribution == 'as-is':
            invited_demand[0] = [math.ceil(d * response_rate) for d in invitation]
            for t in range(1, len(invitation)):
                invited_demand[t] = [0]*len(invitation)

            return [math.ceil(d * response_rate) for d in invitation], demand_spillover, invited_demand
        elif distribution == 'poisson':
            lam = 4

            if invitation is None:
                return new_demand, demand_spillover, invited_demand

            for t in range(len(invitation)):
                # print(lam, demand[t])
                dist = list(np.random.poisson(lam, math.ceil(invitation[t] * response_rate)))
                # print(dist)
                invited_demand[t] = [0]*len(invitation)

                for i in dist:
                    if t+i < len(new_demand):
                        new_demand[t+i] += 1
                        invited_demand[t][t+i] = dist[i]
                    else:
                        demand_spillover += 1
            # print(new_demand)
            return new_demand, demand_spillover, invited_demand
        else:
            '''
            NOTE custom dist returns # attivals at time t
            '''
            for t in range(len(invitation)):
                # dist = self.custom_dist(custom_dist[f'{distribution}_mean'], math.ceil(invitation[t] * response_rate), custom_dist[f'{distribution}_sd'])
                dist = self.custom_dist(self.distribution.mean(), math.ceil(invitation[t] * response_rate), self.distribution.sd())
                invited_demand[t] = [0]*len(invitation)

                for i in range(len(dist)):
                    if t+i < len(new_demand):
                        new_demand[t+i] += dist[i]
                        invited_demand[t][t+i] = dist[i]
                    else:
                        demand_spillover += dist[i]
            return new_demand, demand_spillover, invited_demand


    def custom_dist(self, dist, total, sd=None):
        ''' Output is expected number of arrivals at period 't'
        '''
        if self.params.get('randomised_demand') == True:
            if sd is not None:
                return [max(0, int(normal(dist[i]* total, math.sqrt(sd[i]*total)) )) for i in range(len(dist))]
            else:
                return [int(i*total) for i in dist]
        else:
            return [int(i*total) for i in dist]


    def total_arrival(self):

        return sum(self.arrival)

    def initialize_new_period(self, time):
        ''''''
        self.time = time # Move clock forward

    def generate_next(self):
        ''' '''

        if self.time >= len(self.arrival):
            return  None

        invited_time = -1

        if self.demand[self.time] > self.arrival[self.time]: # must be if instead of while
            tot_invited = 0
            for wave in range(0, self.params['duration'], self.invitation_freq):
                tot_invited += self.invited_demand[wave][self.time]
                if self.arrival[self.time] < tot_invited:
                    # invited_time = wave * self.invitation_freq
                    invited_time = wave
                    break

            person = Person(self.params, self.time, invited_time, len(self.distribution.mean()))
            self.arrival[self.time] += 1

            return person

        return None
