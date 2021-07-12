import json, os
import numpy as np

demand_types = ['old', '7', '6', '5', '4', '3']
location_types = ['vc', 'poly', 'mobile']
vaccine_types = ['Pfizer', 'Moderna']


class Params:

    def read_params(self):

        # dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.path.dirname(os.path.realpath(__file__)) + "/inputs/scenario"

        # scenarios = [f for f in os.listdir(dir_path) if (f.find('params') >= 0 and f.find('.json') >= 0)]
        scenarios = [f for f in os.listdir(dir_path) if f.find('.json') >= 0]

        params = {}

        for scenario in scenarios:
            # print(scenario)
            with open(f"{dir_path}/{scenario}") as params_file:
                scenario_params = json.load(params_file)
                for k, v in scenario_params.items():
                    params[k] = v

        return params

        # with open("params.json") as params_file:
        #     params = json.load(params_file)
        #     return params

    def get_scenarios(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))

        scenarios = [f for f in os.listdir(f'{dir_path}/results') if (f.find('params') >= 0 and f.find('.json') >= 0)]

        params = {}

        for scenario in scenarios:
            with open(scenario) as params_file:
                scenario_params = json.load(params_file)
                for k, v in scenario_params.items():
                    params[k] = v

        # return params
        return [k for k,_ in params.items()]

        # with open("params.json") as params_file:
        #     params = json.load(params_file)
        #     return [k for k,_ in params.items()]


    @classmethod
    def get_appt_book(cls, params, vac, location_type='All', mode='Planning'):

        if mode == 'Planning':
            planning_duration = params['planning_duration'] if params.get('planning_duration') is not None else params['duration']
        elif mode == 'Simulation':
            planning_duration = params['duration']
        else:
            raise Exception('Unknown mode to get_appt_book')

        # curr_appt_first_sum = [0] * params['duration']
        # curr_appt_second_sum = [0] * params['duration']
        curr_appt_first_sum = [0] * planning_duration
        curr_appt_second_sum = [0] * planning_duration
        # for vac in vaccine_types:

        location = params['vaccine_settings'][vac]['location']
        curr_appt_first = params['vaccine_settings'][vac]['appt_book']['first_dose']
        curr_appt_second = params['vaccine_settings'][vac]['appt_book']['second_dose']

        # epoch_length = params['duration'] #+ params['vaccine_settings'][vac]['second_shot_gap'] + params['vaccine_settings'][vac]['max_second_shot_delay']
        epoch_length = planning_duration
        c = [0] * epoch_length
        if location_type == 'All':
            for loc in location_types:
                c = np.add(c, np.multiply(curr_appt_first[loc][:epoch_length], location[loc][:epoch_length]))
        else:
            c = np.add(c, np.multiply(curr_appt_first[location_type][:epoch_length], location[location_type][:epoch_length]))
        c = c.tolist()
        if len(curr_appt_first_sum) < len(c):
            curr_appt_first_sum.extend([0] * (len(c) - len(curr_appt_first_sum)) )
        elif len(curr_appt_first_sum) > len(c):
            c.extend([0] * (len(curr_appt_first_sum) - len(c)) )
        curr_appt_first_sum = np.add(curr_appt_first_sum, c)
        # curr_appt_first_sum = curr_appt_first_sum.tolist()

        c = [0] * epoch_length
        if location_type == 'All':
            for loc in location_types:
                c = np.add(c, np.multiply(curr_appt_second[loc][:epoch_length], location[loc][:epoch_length]))
        else:
            c = np.add(c, np.multiply(curr_appt_second[location_type][:epoch_length], location[location_type][:epoch_length]))
        c = c.tolist()
        if len(curr_appt_second_sum) < len(c):
            curr_appt_second_sum.extend([0] * (len(c) - len(curr_appt_second_sum)) )
        elif len(curr_appt_second_sum) > len(c):
            c.extend([0] * (len(curr_appt_second_sum) - len(c)) )
        curr_appt_second_sum = np.add(curr_appt_second_sum, c)
        # curr_appt_second_sum = curr_appt_second_sum.tolist()

        total_appt_book = np.add(curr_appt_first_sum, curr_appt_second_sum)

        return  curr_appt_first_sum.tolist(), curr_appt_second_sum.tolist(), total_appt_book.tolist()
