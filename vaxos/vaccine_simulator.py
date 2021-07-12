import math, json, os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from random import shuffle, random
from datetime import datetime, date

from vaxos.params import Params, demand_types, location_types, vaccine_types

from vaxos.population import Population
from vaxos.vaccine_center_collection import VaccineCenterCollection

from vaxos.optimal_booking_limit_solver import OptimalBookingLimitSolver
from vaxos.optimal_invitation_gen_solver import OptimalInvitationGenSolver

from vaxos.db.status import Status


def df_to_plotly(df):
    return {'z': df.values.tolist(),
            'x': df.columns.tolist(),
            'y': df.index.tolist()}


class VaccineSimulator:

    vaccine_centers = None
    population = None
    stats = {}
    occupancy = {}
    person_rank = {}
    params = None

    def __init__(self, params):

        self.params = params
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.dir_path = dir_path

        self.init_date = datetime.now()

        try:
            status = Status(
                scenario_name=self.params['name'],
                init_date=self.init_date,
                history='Start',
                current='Processing',
                status='In Progress',
            )
            status.save()
        except: pass

        self.stats['scenario_name'] = self.params['name']


        for vac in vaccine_types:
            vaccine_params = self.params["vaccine_settings"][vac]

            epoch_length = self.params['duration'] + vaccine_params['second_shot_gap'] + vaccine_params['max_second_shot_delay']

            for loc, _ in vaccine_params['location'].items():

                if len(vaccine_params['location'][loc]) < epoch_length:
                    vaccine_params['location'][loc] = vaccine_params['location'][loc] + ([vaccine_params['location'][loc][-1]] * (epoch_length - len(vaccine_params['location'][loc])))

                if len(vaccine_params['appt_book']['first_dose'][loc]) < epoch_length:
                    vaccine_params['appt_book']['first_dose'][loc] = vaccine_params['appt_book']['first_dose'][loc] + ([0] * (epoch_length - len(vaccine_params['appt_book']['first_dose'][loc])))
                if len(vaccine_params['appt_book']['second_dose'][loc]) < epoch_length:
                    vaccine_params['appt_book']['second_dose'][loc] = vaccine_params['appt_book']['second_dose'][loc] + ([0] * (epoch_length - len(vaccine_params['appt_book']['second_dose'][loc])))

                if len(vaccine_params['first_dose_booking_limit']) < epoch_length:
                    vaccine_params['first_dose_booking_limit'] = vaccine_params['first_dose_booking_limit'] + ([0] * (epoch_length - len(vaccine_params['first_dose_booking_limit'])))
                if len(vaccine_params['second_dose_booking_limit']) < epoch_length:
                    vaccine_params['second_dose_booking_limit'] = vaccine_params['second_dose_booking_limit'] + ([0] * (epoch_length - len(vaccine_params['second_dose_booking_limit'])))



        # if params is None:
        #     # self.params = Params.params
        #     self.params = Params.toy_0_params
        # else:

        # if params['booking_limits_solver'] == "None":
        if self.params['booking_limits_solver'] == "lp":
            for vac in vaccine_types:
                try:
                    status = Status.get((Status.scenario_name == self.params['name']) & (Status.init_date == self.init_date))

                    (Status.update({
                        Status.history: status.history + f" >> {status.current}",
                        Status.current: f'Solver: Booking Limits LP {vac}',
                        })
                        .where((Status.scenario_name == self.params['name']) & (Status.init_date == self.init_date))
                        .execute())
                except: pass

                solver = OptimalBookingLimitSolver(self.params, self.init_date)
                self.params = solver.solve(vac)
            # print(self.params)

        self.stats['booking_limits'] = {}
        for vac in vaccine_types:
            self.stats['booking_limits'][vac] = {
                'first_dose': [int(x) for x in self.params['vaccine_settings'][vac]['first_dose_booking_limit']],
                'second_dose': [int(x) for x in self.params['vaccine_settings'][vac]['second_dose_booking_limit']]
            }

        try:
            status = Status.get((Status.scenario_name == self.params['name']) & (Status.init_date == self.init_date))
            (Status.update({
                Status.history: status.history + f" >> {status.current}",
                Status.current: f'Solver: Invitation Gen - {self.params["invitation_gen_solver"]}',
                })
                .where((Status.scenario_name == self.params['name']) & (Status.init_date == self.init_date))
                .execute())
        except: pass
        if self.params['invitation_gen_solver'] == "cop" or self.params['invitation_gen_solver'] == "lp":

            solver = OptimalInvitationGenSolver(self.params, self.init_date)
            self.params = solver.solve()


        self.stats['invitation'] = [int(x) for x in self.params['invitation']]


        # # with open(f"{dir_path}/archive/scenario/{self.params['name']}.json", 'w+') as archive_file:
        # with open(f"{dir_path}/inputs/scenario/{self.params['name']}.json", 'w+') as params_file:
        #     json.dump({self.params['name']: self.params}, params_file)


    def save(self):
        # with open("dashboard.json") as dashboard_file:
        #     dashboard = json.load(dashboard_file)
        results_dir = f"{self.dir_path}/results/{self.params['name']}"
        os.makedirs(results_dir, exist_ok=True)

        print(f'Saving results to {results_dir}')


        person_rank_df = pd.DataFrame.from_dict(self.person_rank, orient='index')
        occupancy_df = None
        for vac in vaccine_types:
            if occupancy_df is None:
                occupancy_df = pd.DataFrame.from_dict(self.vaccine_center_collection[vac].occupancy, orient='index')
            else:
                occupancy_df = occupancy_df.append(pd.DataFrame.from_dict(self.vaccine_center_collection[vac].occupancy, orient='index'))

        # occupancy_df = pd.DataFrame.from_dict(self.vaccine_centers.occupancy, orient='index')
        arrival_df = pd.DataFrame(self.population.arrival)


        person_rank_df.to_csv(f"{results_dir}/person_rank_df.csv")
        occupancy_df.to_csv(f"{results_dir}/occupancy_df.csv")
        arrival_df.to_csv(f"{results_dir}/arrival_df.csv")

        with open(f"{results_dir}/results.json", 'w') as results_file:
            json.dump({'params': self.params, 'stats': self.stats}, results_file)

        if os.path.exists(f"{results_dir}/dashboard.json"):
            os.remove(f"{results_dir}/dashboard.json")

        # return dashboard[self.params['name']]
        # return dashboard

    def simulate(self):
        ''' '''
        # if params is None:
        #     params = Params.params

        try:
            status = Status.get((Status.scenario_name == self.params['name']) & (Status.init_date == self.init_date))
            (Status.update({
                Status.history: status.history + f" >> {status.current}",
                Status.current: f'Simulation',
                })
                .where((Status.scenario_name == self.params['name']) & (Status.init_date == self.init_date))
                .execute())
        except: pass

        simulation_length = self.params['duration']
        # epoch_length = self.params['duration'] + self.params['second_shot_gap'] + self.params['max_second_shot_delay']

        # occupancy = {}
        # person_rank = {}
        # stats = {}
        p = 0

        self.vaccine_center_collection = {vac: VaccineCenterCollection(self.params, vac) for vac in vaccine_types}
        # self.vaccine_centers = VaccineCenterCollection(self.params)
        self.population = Population(self.params)
        self.stats['invitation'] = self.population.invitations
        self.stats['Spillover Appointments'] = self.population.demand_spillover / self.params['scale_factor']
        # self.stats['Booked Appointments'] = 0
        self.stats['Booked Appointments'] = {'All': 0}
        # self.stats['Missed Appointments'] = 0
        self.stats['Missed Appointments'] = {'All': 0}
        self.stats['Capacity'] = {vac: self.vaccine_center_collection[vac].get_total_capacity() for vac in vaccine_types} # / self.params['scale_factor']
        self.stats['Arrival'] = self.population.arrival # / self.params['scale_factor']
        # print(f"Demand Spillover: {self.population.demand_spillover}")

        vaccine_params = {}

        for simulation_time in range(simulation_length):
            print(f"Simulation Time: {simulation_time}, {datetime.now()}")
            self.population.initialize_new_period(simulation_time)
            # capacity = vaccine_centers.get_capacity(simulation_time)

            while True:
                person = self.population.generate_next()
                if person == None:
                    break

                if self.stats['Booked Appointments'].get(f'Wave {person.appt_time}') is None:
                    self.stats['Booked Appointments'][f'Wave {person.appt_time}'] = 0
                    self.stats['Missed Appointments'][f'Wave {person.appt_time}'] = 0

                person_utility_index, sorted_utility = person.generate_utility()

                preference_rank = 1
                second_check = 0
                appointment_booked = False
                for idx in sorted_utility:
                    space_time = person_utility_index[idx]
                    vac = None
                    for v in vaccine_types:
                        if space_time[0].find(v) > 0:
                            vac = v
                            vaccine_params = self.params['vaccine_settings'][vac]
                            break

                    # if space_time[1] >= 15:
                    #     print(p, space_time, 1, self.vaccine_center_collection[vac].is_available(space_time, 1))
                    # if (vaccine_centers.get_occupancy(space_time)['first_shot'] + vaccine_centers.get_occupancy(space_time)['second_shot'] < vaccine_centers.get_capacity(space_time)):


                    # if self.vaccine_center_collection[vac].is_available(space_time, 1) == True:
                    if True:
                        # if self.vaccine_center_collection[vac].supply[space_time[1]] <= self.vaccine_center_collection[vac].cumulative_consumption[space_time[1]]:
                        #     raise Exception("Consumption exceeds supply Dose 1")

                        # for n in range(self.params['second_shot_gap'], self.params['second_shot_gap'] + self.params['max_second_shot_delay']+1):
                        for n in range(vaccine_params['second_shot_gap'], vaccine_params['second_shot_gap'] + vaccine_params['max_second_shot_delay']+1):
                            second_check += 1
                            space_time_2 = (space_time[0], space_time[1] + n)

                            # print(p, space_time_2, 2, self.vaccine_center_collection[vac].is_available(space_time_2, 2))

                            # # if (vaccine_centers.get_occupancy(space_time_2)['first_shot'] + vaccine_centers.get_occupancy(space_time_2)['second_shot'] < vaccine_centers.get_capacity(space_time)):
                            # if self.vaccine_center_collection[vac].is_available(space_time_2, 2) == True:
                            if self.vaccine_center_collection[vac].is_available_2(space_time, space_time_2) == True:

                                # if self.vaccine_center_collection[vac].supply[space_time_2[1]] <= self.vaccine_center_collection[vac].cumulative_consumption[space_time_2[1]]:
                                #     raise Exception("Consumption exceeds supply Dose 1")

                                # vaccine_centers.get_occupancy(space_time)['first_shot'] += 1
                                # vaccine_centers.get_occupancy(space_time_2)['second_shot'] += 1
                                self.vaccine_center_collection[vac].add_appointment(space_time, space_time_2)

                                self.person_rank[p] = {
                                    'space_time': space_time,
                                    'location': space_time[0],
                                    'period': space_time[1],
                                    'arrival_time': simulation_time,
                                    'waiting_time': space_time[1] - simulation_time,
                                    'preference_rank': preference_rank,
                                    'location_rank': person.get_loc_rank(space_time[0]),
                                    'appt_time': person.appt_time,
                                    'appt_waiting_time': space_time[1] - person.appt_time,
                                    'vaccine': vac,
                                }

                                appointment_booked = True
                                # self.stats['Booked Appointments'] += 1
                                self.stats['Booked Appointments']['All'] += 1 / self.params['scale_factor']
                                self.stats['Booked Appointments'][f'Wave {person.appt_time}'] += 1 / self.params['scale_factor']

                                break

                    if appointment_booked == True:
                        break

                    preference_rank += 1


                if appointment_booked == False:

                    # self.stats['Missed Appointments'] += 1
                    self.stats['Missed Appointments']['All'] += 1 / self.params['scale_factor']
                    self.stats['Missed Appointments'][f'Wave {person.appt_time}'] += 1 / self.params['scale_factor']

                    self.person_rank[p] = {
                        'space_time': space_time,
                        'location': 'Unassigned',
                        'period': -1,
                        'arrival_time': simulation_time,
                        # 'waiting_time': -1,
                        'waiting_time': min(self.params['utility']['limit_time_preference'], max(0, self.params['duration'] - simulation_time)),
                        'preference_rank': -1,
                        'location_rank': -1,
                        'appt_time': person.appt_time,
                        # 'appt_waiting_time': -1,
                        'appt_waiting_time': min(self.params['utility']['limit_time_preference'] + self.params['invitation_frequency'], max(0, self.params['duration'] - person.appt_time)),
                        'vaccine': vac,
                    }
                    # print(preference_rank, second_check)
                    # print(self.vaccine_centers.cumulative_second_dose_consumption)
                    # print(self.person_rank[p])
                    # print(sorted_utility)

                # if self.person_rank[p]['waiting_time'] < 0:
                #     print('waiting_time', person.appt_time, simulation_time, self.person_rank[p]['waiting_time'])
                # if self.person_rank[p]['appt_waiting_time'] < 0:
                #     print('appt_waiting_time', person.appt_time, simulation_time, self.person_rank[p]['appt_waiting_time'])

                p += 1

            # print(f"Total Bookings: {population.total_bookings()}")
            # print(f"Capacity: {capacity}")

        person_rank_df = pd.DataFrame.from_dict(self.person_rank, orient='index')
        occupancy_df = None
        for vac in vaccine_types:
            if occupancy_df is None:
                occupancy_df = pd.DataFrame.from_dict(self.vaccine_center_collection[vac].occupancy, orient='index')
            else:
                occupancy_df = occupancy_df.append(pd.DataFrame.from_dict(self.vaccine_center_collection[vac].occupancy, orient='index'))
        # occupancy_df = pd.DataFrame.from_dict(self.vaccine_centers.get_scaled_occupancy(), orient='index')
#         # print(person_rank_df)

#         person_rank_df.to_csv('person_rank.csv')
        occupancy_df.to_csv('occupancy.csv')

        slots_assigned = person_rank_df[person_rank_df['preference_rank'] >= 0]

        avg_wait_time_skip_missed = {
            'All': slots_assigned['waiting_time'].mean()
        }
        avg_appt_wait_time_skip_missed = {
            'All': slots_assigned['appt_waiting_time'].mean()
        }
        avg_wait_time_include_missed = {
            'All': person_rank_df['waiting_time'].mean()
        }
        avg_appt_wait_time_include_missed = {
            'All': person_rank_df['appt_waiting_time'].mean()
        }
        for vac in vaccine_types:
            avg_wait_time_skip_missed[vac] = slots_assigned[slots_assigned['vaccine'] == vac]['waiting_time'].mean()
            avg_appt_wait_time_skip_missed[vac] = slots_assigned[slots_assigned['vaccine'] == vac]['appt_waiting_time'].mean()
            avg_wait_time_include_missed[vac] = person_rank_df[person_rank_df['vaccine'] == vac]['waiting_time'].mean()
            avg_appt_wait_time_include_missed[vac] = person_rank_df[person_rank_df['vaccine'] == vac]['appt_waiting_time'].mean()

        self.stats['Avg Waiting Time (Missed Appts == 0 Wait)'] = avg_wait_time_skip_missed
        self.stats['Avg Appt Waiting Time (Missed Appts == 0 Wait)'] = avg_appt_wait_time_skip_missed

        self.stats['Avg Waiting Time (Missed appts == Max Wait)'] = avg_wait_time_include_missed
        self.stats['Avg Appt Waiting Time (Missed appts == Max Wait)'] = avg_appt_wait_time_include_missed

        # self.stats['Avg Preference (Location & Time)'] = slots_assigned['preference_rank'].mean()
        self.stats['Avg Preference (Location)'] = slots_assigned['location_rank'].mean()
        self.stats['Total Throughput'] = self.stats['Booked Appointments']['All']
        self.stats['Daily Throughout'] = self.stats['Booked Appointments']['All'] / simulation_length

        self.stats['TPut Percentile (by Period)'] = {
            '0.5': person_rank_df[person_rank_df['period'] != -1]['period'].quantile(0.5),
            '0.75': person_rank_df[person_rank_df['period'] != -1]['period'].quantile(0.75),
            '0.9': person_rank_df[person_rank_df['period'] != -1]['period'].quantile(0.9),
            '1': person_rank_df[person_rank_df['period'] != -1]['period'].quantile(1),
        }



        try:
            status = Status.get((Status.scenario_name == self.params['name']) & (Status.init_date == self.init_date))
            (Status.update({
                Status.history: status.history + f" >> {status.current}",
                Status.current: f'End',
                Status.status: f'Completed',
                })
                .where((Status.scenario_name == self.params['name']) & (Status.init_date == self.init_date))
                .execute())
        except: pass

        # print(person_rank_df, occupancy_df)

        return person_rank_df, occupancy_df



