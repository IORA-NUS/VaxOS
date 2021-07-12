
# from vaccine_center import VaccineCenter
import numpy as np

from vaxos.params import location_types, vaccine_types, Params
from vaxos.supply_expiry import SupplyExpiry


class VaccineCenterCollection:
    ''' '''

    def __init__(self, params, vaccine):
        ''' '''
        self.params = params
        self.vaccine = vaccine
        self.vaccine_params = params["vaccine_settings"][vaccine]
        self.epoch_length = params['duration'] + self.vaccine_params['second_shot_gap'] + self.vaccine_params['max_second_shot_delay']

        self.first_dose_appt_book, self.second_dose_appt_book, self.appt_book = Params.get_appt_book(self.params, vaccine)

        # self.first_dose_booking_limit = self.first_dose_appt_book * -1 * params['scale_factor']
        # self.second_dose_booking_limit = self.second_dose_appt_book * -1 * params['scale_factor']

        # self.capacity = [0] * epoch_length
        self.capacity = {}
        self.first_dose_booking_limit = [0] * self.epoch_length
        self.second_dose_booking_limit = [0] * self.epoch_length
        self.occupancy = {}

        self.consumption = [0] * self.epoch_length
        self.cumulative_consumption = [0] * self.epoch_length
        self.cumulative_first_dose_consumption = [0] * self.epoch_length
        self.cumulative_second_dose_consumption = [0] * self.epoch_length

        # self.consumption = (self.appt_book * params['scale_factor']).tolist()
        # self.cumulative_consumption = (self.appt_book.cumsum() * params['scale_factor']).tolist()

        # self.cumulative_first_dose_consumption = (self.first_dose_appt_book.cumsum() * params['scale_factor']).tolist()
        # self.cumulative_second_dose_consumption = (self.second_dose_appt_book.cumsum() * params['scale_factor']).tolist()

        # print(self.consumption)
        # print(self.cumulative_consumption)
        # print(self.cumulative_first_dose_consumption)
        # print(self.cumulative_second_dose_consumption)

        self.supply = SupplyExpiry(self.vaccine_params['supply_scenario']).get_supply_vector(self.params['start_date'], self.epoch_length, state='Supply', vaccine=vaccine, cumulative=True, include_init=False)
        self.supply = [s * params['scale_factor'] for s in self.supply]
        # print(f"Supply {vaccine}: {self.supply}")
        # print(f"appt_book {vaccine}: {appt_book}")
        # self.supply = np.subtract(self.supply, self.appt_book)

        # print(f"Supply {vaccine}: {self.supply}")
        # print(self.first_dose_booking_limit)
        # print(self.second_dose_booking_limit)

        # self.cumulative_second_dose_blocked_supply = [0] * self.epoch_length
        # print(vaccine, self.epoch_length)

        for t in range(self.epoch_length):
            # if t > 0:
            #     self.cumulative_second_dose_blocked_supply[t] = self.cumulative_second_dose_blocked_supply[t-1]

            try:
                if t > 0:
                    self.first_dose_booking_limit[t] = self.first_dose_booking_limit[t-1]
                    self.second_dose_booking_limit[t] = self.second_dose_booking_limit[t-1]

                # self.first_dose_booking_limit[t] += self.vaccine_params["first_dose_booking_limit"][t] * params['scale_factor']
                # self.second_dose_booking_limit[t] += self.vaccine_params["second_dose_booking_limit"][t] * params['scale_factor']

                if t % params['booking_limit_control_duration'] == 0:
                    start = (t // params['booking_limit_control_duration']) * params['booking_limit_control_duration']
                    end = min(start + params['booking_limit_control_duration'], len(self.vaccine_params["first_dose_booking_limit"]))
                    first_dose_duration_sum = sum(self.vaccine_params["first_dose_booking_limit"][start:end])
                    second_dose_duration_sum = sum(self.vaccine_params["second_dose_booking_limit"][start:end])
                    self.first_dose_booking_limit[t] += first_dose_duration_sum * params['scale_factor']
                    self.second_dose_booking_limit[t] += second_dose_duration_sum * params['scale_factor']

            except: pass

            for loc, _ in self.vaccine_params['location'].items():
                # print(loc, t)

                for loc_id in range(self.vaccine_params['location'][loc][t]):
                    self.capacity[(f"{loc}_{vaccine}_{loc_id:02d}", t)] = (self.params['capacity'][loc] - (self.vaccine_params['appt_book']['first_dose'][loc][t] + self.vaccine_params['appt_book']['second_dose'][loc][t])) * params['scale_factor']
                    # try:
                    #     self.capacity[(f"{loc}_{vaccine}_{loc_id:02d}", t)] = (self.params['capacity'][loc] - (self.vaccine_params['appt_book']['first_dose'][loc][t] + self.vaccine_params['appt_book']['second_dose'][loc][t])) * params['scale_factor']
                    # except:
                    #     self.capacity[(f"{loc}_{vaccine}_{loc_id:02d}", t)] = self.params['capacity'][loc]

                    self.occupancy[(f"{loc}_{vaccine}_{loc_id:02d}", t)] = {
                        'location':f"{loc}_{vaccine}_{loc_id:02d}",
                        'period': t,
                        'capacity': self.capacity[(f"{loc}_{vaccine}_{loc_id:02d}", t)],
                        'first_shot': 0, # self.vaccine_params['appt_book']['first_dose'][loc][t] * params['scale_factor'], # 0,
                        'second_shot': 0, #self.vaccine_params['appt_book']['second_dose'][loc][t] * params['scale_factor'], # 0,
                        "vaccine": vaccine,
                    }

        # print(self.capacity)
        # print(self.cumulative_second_dose_blocked_supply)

        # print(self.first_dose_booking_limit)
        # print(self.second_dose_booking_limit)

    # def get_appt_book(self, params, vac):
    #     curr_appt_first_sum = [0] * params['duration']
    #     curr_appt_second_sum = [0] * params['duration']
    #     # for vac in vaccine_types:

    #     location = params['vaccine_settings'][vac]['location']
    #     curr_appt_first = params['vaccine_settings'][vac]['appt_book']['first_dose']
    #     curr_appt_second = params['vaccine_settings'][vac]['appt_book']['second_dose']

    #     epoch_length = params['duration'] + params['vaccine_settings'][vac]['second_shot_gap'] + params['vaccine_settings'][vac]['max_second_shot_delay']
    #     c = [0] * epoch_length
    #     for loc in location_types:
    #         c = np.add(c, np.multiply(curr_appt_first[loc][:epoch_length], location[loc][:epoch_length]))
    #     c = c.tolist()
    #     if len(curr_appt_first_sum) < len(c):
    #         curr_appt_first_sum.extend([0] * (len(c) - len(curr_appt_first_sum)) )
    #     elif len(curr_appt_first_sum) > len(c):
    #         c.extend([0] * (len(curr_appt_first_sum) - len(c)) )
    #     curr_appt_first_sum = np.add(curr_appt_first_sum, c)
    #     curr_appt_first_sum = curr_appt_first_sum.tolist()

    #     c = [0] * epoch_length
    #     for loc in location_types:
    #         c = np.add(c, np.multiply(curr_appt_second[loc][:epoch_length], location[loc][:epoch_length]))
    #     c = c.tolist()
    #     if len(curr_appt_second_sum) < len(c):
    #         curr_appt_second_sum.extend([0] * (len(c) - len(curr_appt_second_sum)) )
    #     elif len(curr_appt_second_sum) > len(c):
    #         c.extend([0] * (len(curr_appt_second_sum) - len(c)) )
    #     curr_appt_second_sum = np.add(curr_appt_second_sum, c)
    #     # curr_appt_second_sum = curr_appt_second_sum.tolist()

    #     total_appt_book = np.add(curr_appt_first_sum, curr_appt_second_sum)

    #     return  curr_appt_first_sum, curr_appt_second_sum, total_appt_book



    def get_capacity(self, space_time, shot='all'):
        # if shot == 1:
        #     return self.first_shot_limit[space_time]
        # elif shot == 2:
        #     return self.second_shot_limit[space_time]
        # else:
        #     return self.capacity[space_time]
        return self.capacity[space_time]

    def get_total_capacity(self):
        total_capacity = {loc: [0] * self.epoch_length for loc in location_types}
        for loc in location_types:
            for t in range(self.epoch_length):
                for k, v in self.capacity.items():
                    if k[1] == t and loc ==k[0][:k[0].find("_")]:
                        total_capacity[loc][t] += v

        return total_capacity

    def get_occupancy(self, space_time):
        return self.occupancy[space_time]

    def is_available(self, space_time, shot):
        # if self.params['supply_limit'] == True:
        if self.vaccine_params['supply_limit'] == True:
            total_consumption = sum(self.consumption[:space_time[1]+1])
            # total_consumption = self.cumulative_consumption[space_time[1]]
            total_supply = self.supply[space_time[1]]
            # total_supply = self.supply[space_time[1]] - self.appt_book[space_time[1]]
        else:
            total_consumption = 0
            total_supply = 1

        if shot == 1:
            if self.params["booking_limit_strategy"] in ["Both", "First"]:
                return (total_supply > total_consumption) and \
                    (self.first_dose_booking_limit[space_time[1]] > self.cumulative_first_dose_consumption[space_time[1]]) and \
                    (self.get_occupancy(space_time)['first_shot'] + self.get_occupancy(space_time)['second_shot'] < self.get_capacity(space_time, 'all'))
            else: # NO Booking limit strategy
                return (total_supply > total_consumption) and \
                    (self.get_occupancy(space_time)['first_shot'] + self.get_occupancy(space_time)['second_shot'] < self.get_capacity(space_time, 'all'))

        elif shot == 2:
            if self.params["booking_limit_strategy"] in ["Both", "Second"]:
                return (total_supply > total_consumption) and \
                    (self.second_dose_booking_limit[space_time[1]] > self.cumulative_second_dose_consumption[space_time[1]]) and \
                    (self.get_occupancy(space_time)['first_shot'] + self.get_occupancy(space_time)['second_shot'] < self.get_capacity(space_time, 'all'))
            else:
                return (total_supply > total_consumption) and \
                    (self.get_occupancy(space_time)['first_shot'] + self.get_occupancy(space_time)['second_shot'] < self.get_capacity(space_time, 'all'))


    def is_available_2(self, space_time, space_time_2):

        # supply_breach = False
        if self.vaccine_params['supply_limit'] == True:
            for i in range(space_time[1], space_time_2[1]+1):
                if self.cumulative_consumption[i] > self.supply[i]:
                    # supply_breach = True
                    # if self.vaccine == 'Moderna':
                    #     print(f'{self.vaccine}: Supply Breached')
                    return False
                    # break

        # capacity_breach = False
        # for i in range(space_time[1], space_time_2[1]+1):
        #     new_space_time = (space_time[0], i)
        if self.get_occupancy(space_time)['first_shot'] + self.get_occupancy(space_time)['second_shot'] > self.get_capacity(space_time):
            # capacity_breach = True
            # if self.vaccine == 'Moderna':
            #     print(f"{self.vaccine}: Capacity Breached, First: {self.get_occupancy(new_space_time)['first_shot']}, Second: {self.get_occupancy(new_space_time)['second_shot']}, {new_space_time}: {self.get_capacity(new_space_time)}")
            return False

        if self.get_occupancy(space_time_2)['first_shot'] + self.get_occupancy(space_time_2)['second_shot'] > self.get_capacity(space_time_2):
            # capacity_breach = True
            # if self.vaccine == 'Moderna':
            #     print(f"{self.vaccine}: Capacity Breached, First: {self.get_occupancy(new_space_time)['first_shot']}, Second: {self.get_occupancy(new_space_time)['second_shot']}, {new_space_time}: {self.get_capacity(new_space_time)}")
            return False
            # break

        if self.params["booking_limit_strategy"] == "First":
            return (self.first_dose_booking_limit[space_time[1]] > self.cumulative_first_dose_consumption[space_time[1]])
        elif self.params["booking_limit_strategy"] == "Second":
            return (self.second_dose_booking_limit[space_time_2[1]] > self.cumulative_second_dose_consumption[space_time_2[1]])
        elif self.params["booking_limit_strategy"] == "Both":
            return (self.first_dose_booking_limit[space_time[1]] > self.cumulative_first_dose_consumption[space_time[1]]) and \
                (self.second_dose_booking_limit[space_time_2[1]] > self.cumulative_second_dose_consumption[space_time_2[1]])
        else:
            return True


    def add_appointment(self, space_time, space_time_2):
        self.occupancy[space_time]['first_shot'] += 1
        self.occupancy[space_time_2]['second_shot'] += 1

        self.consumption[space_time[1]] += 1
        self.consumption[space_time_2[1]] += 1

        for i in range(space_time[1], self.epoch_length):
            self.cumulative_first_dose_consumption[i] += 1
            self.cumulative_consumption[i] += 1

        for i in range(space_time_2[1], self.epoch_length):
            self.cumulative_second_dose_consumption[i] += 1
            self.cumulative_consumption[i] += 1


    # def get_scaled_occupancy(self):
    #     scaled_occupancy = self.occupancy.copy()

    #     for k, _ in scaled_occupancy:
    #         scaled_occupancy[k]['capacity'] = scaled_occupancy[k]['capacity'] / self.params['scale_factor']
    #         scaled_occupancy[k]['first_shot'] = scaled_occupancy[k]['first_shot'] / self.params['scale_factor']
    #         scaled_occupancy[k]['second_shot'] = scaled_occupancy[k]['second_shot'] / self.params['scale_factor']

