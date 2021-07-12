import traceback

import openpyxl, os, json, shutil
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, date
import multiprocessing as mp
from multiprocessing import Pool
from copy import deepcopy

from vaxos.params import location_types, vaccine_types, Params

from vaxos.vaccine_simulator import VaccineSimulator
from vaxos.supply_expiry import SupplyExpiry

from vaxos.db.file_upload import FileUpload

class ExcelScenarioLoader:

    start_date = None
    duration = None

    def __init__(self, filename):

        self.processing_date = datetime.now()

        # print('inside ExcelScenarioLoader')
        try:
            file_upload = FileUpload(
                file_name=filename,
                processing_date=self.processing_date,
                status='In Progress',
            )
            file_upload.save()
        except: pass
        # print('file_upload record saved')
        # print(file_upload)


        self.filename = filename
        self.inputs_dir_path = os.path.dirname(os.path.realpath(__file__)) + '/inputs'
        self.archive_dir_path = os.path.dirname(os.path.realpath(__file__)) + '/archive/excel'
        os.makedirs(self.archive_dir_path, exist_ok=True)


        self.scenario_name = self.filename.replace(' ', '_')
        self.scenario_name = self.scenario_name[:self.scenario_name.find('.')]

        self.supply_scenario_name = self.scenario_name + '_supply'
        self.dist_name = self.scenario_name + '_dist'

        try:

            self.settings_df = pd.read_excel(f"{self.inputs_dir_path}/excel/{filename}", 'Settings')
            # print(self.settings_df)
            self.distribution_df = pd.read_excel(f"{self.inputs_dir_path}/excel/{filename}", 'Distribution')
            self.supply_df = pd.read_excel(f"{self.inputs_dir_path}/excel/{filename}", 'Supply')
            self.appt_book_df = pd.read_excel(f"{self.inputs_dir_path}/excel/{filename}", 'ApptBook')
            self.manual_policy_df = pd.read_excel(f"{self.inputs_dir_path}/excel/{filename}", 'ManualPolicy')

            self.create_distribution()
            self.create_supply()
            try:
                self.scenario_list = self.create_scenario_params()
            except Exception as e:
                print("Exception", e)
                # self.scenario_list = []
                raise e


            (FileUpload.update({
                FileUpload.status: f'Success',
                })
                .where((FileUpload.file_name == filename) & (FileUpload.processing_date == self.processing_date))
                .execute())

        except:
            (FileUpload.update({
                FileUpload.status: f'Failed',
                })
                .where((FileUpload.file_name == filename) & (FileUpload.processing_date == self.processing_date))
                .execute())

            return

        self.params_dict = Params().read_params()
        shutil.move(f"{self.inputs_dir_path}/excel/{filename}", f"{self.archive_dir_path}/{filename}")


    def create_supply(self):
        ''''''
        self.supply_df.to_csv(f"{self.inputs_dir_path}/supply/{self.supply_scenario_name}.csv", index=False)

    def create_distribution(self):
        ''''''
        self.distribution_df.to_csv(f"{self.inputs_dir_path}/custom_dist/{self.dist_name}.csv", index=False)

    def create_scenario_params(self):
        ''''''
        with open(f"{self.inputs_dir_path}/template/params_template.json") as template_file:
            params_template = json.load(template_file)

        appt_book_df = self.appt_book_df.sort_values('date')
        appt_book_df.reset_index(inplace=True)

        manual_policy_df = self.manual_policy_df.sort_values('date')
        manual_policy_df.reset_index(inplace=True)

        # start_date = appt_book_df['date'].min()
        # self.start_date = self.settings_df[self.settings_df['variable'] == f'start_date'].reset_index().at[0, 'value']
        # self.start_date = datetime.strftime(self.start_date, "%Y-%m-%d")
        # self.duration = self.settings_df[self.settings_df['variable'] == f'duration'].reset_index().at[0, 'value']
        self.start_date = self.settings_df[self.settings_df['variable'] == f'start_date'].reset_index().at[0, 'All']
        self.start_date = datetime.strftime(self.start_date, "%Y-%m-%d")
        self.duration = int(self.settings_df[self.settings_df['variable'] == f'duration'].reset_index().at[0, 'All'])

        try:
            self.planning_duration = int(self.settings_df[self.settings_df['variable'] == f'planning_duration'].reset_index().at[0, 'All'])
        except:
            self.planning_duration = self.duration


        # print(start_date, duration)
        # params_template['utility']['vaccine_bias']['vaccine'] = self.settings_df[self.settings_df['variable'] == 'Vaccine_preference'].reset_index().at[0, 'value']
        # params_template['utility']['vaccine_bias']['bias'] = self.settings_df[self.settings_df['variable'] == 'Vaccine_preference_ratio'].reset_index().at[0, 'value']
        params_template['utility']['vaccine_bias']['vaccine'] = self.settings_df[self.settings_df['variable'] == 'vaccine_preference'].reset_index().at[0, 'All']
        params_template['utility']['vaccine_bias']['bias'] = float(self.settings_df[self.settings_df['variable'] == 'vaccine_preference_ratio'].reset_index().at[0, 'All'])

        params_template['start_date'] = self.start_date #datetime.strptime(start_date, 'yyyy-mm-dd')
        params_template['duration'] = int(self.duration) #datetime.strptime(start_date, 'yyyy-mm-dd')
        params_template['planning_duration'] = int(self.planning_duration) #datetime.strptime(start_date, 'yyyy-mm-dd')
        params_template['supply_scenario_display'] = self.supply_scenario_name
        # params_template['booking_limit_strategy'] = 'First'
        # params_template['booking_limits_solver'] = 'None'
        # params_template['invitation_gen_solver'] = 'None'
        # params_template['risk'] = 0
        params_template['booking_limit_strategy'] = self.settings_df[self.settings_df['variable'] == f'booking_limit_strategy'].reset_index().at[0, 'All']
        params_template['booking_limits_solver'] = self.settings_df[self.settings_df['variable'] == f'booking_limits_solver'].reset_index().at[0, 'All']
        params_template['invitation_gen_solver'] = self.settings_df[self.settings_df['variable'] == f'invitation_gen_solver'].reset_index().at[0, 'All']
        params_template['tput_weight'] = self.settings_df[self.settings_df['variable'] == f'tput_weight'].reset_index().at[0, 'All']
        params_template['risk'] = int(self.settings_df[self.settings_df['variable'] == f'risk'].reset_index().at[0, 'All'])
        params_template['distribution'] = self.dist_name

        if params_template['invitation_gen_solver'] == 'heuristic':
            params_template['demand_generator'] = 'Target'
        else:
            params_template['demand_generator'] = 'Invited'

        computed_vals = {}
        for vac in vaccine_types:
            # print(vac)
            # num_vc = self.settings_df[self.settings_df['variable'] == f'{vac}_num_vc'].reset_index().at[0, 'value']
            # num_poly = self.settings_df[self.settings_df['variable'] == f'{vac}_num_poly'].reset_index().at[0, 'value']
            num_vc = self.settings_df[self.settings_df['variable'] == f'num_vc'].reset_index().at[0, vac]
            num_poly = self.settings_df[self.settings_df['variable'] == f'num_poly'].reset_index().at[0, vac]

            # print(num_vc)
            # print(num_poly)

            vc_part = 0 if num_vc == 0 else ((num_vc * params_template['capacity']['vc']) / ((num_vc * params_template['capacity']['vc']) + (num_poly * params_template['capacity']['poly']))) / num_vc
            poly_part = 0 if num_poly == 0 else ((num_poly * params_template['capacity']['poly']) / ((num_vc * params_template['capacity']['vc']) + (num_poly * params_template['capacity']['poly']))) / num_poly

            computed_vals[vac] = {
                'num_vc': int(num_vc),
                'num_poly': int(num_poly),
                'vc_part': float(vc_part),
                'poly_part': float(poly_part)
            }

        # print(computed_vals)
        # print('Level 1')

        # This is a separate loop because computed_vals[vac] needs to be calculated before updating appt_book
        for vac in vaccine_types:
            try:
                params_template['vaccine_settings'][vac]['risk'] = int(self.settings_df[self.settings_df['variable'] == f'risk'].reset_index().at[0, vac])
            except: pass
            params_template['vaccine_settings'][vac]['second_shot_gap'] = int(self.settings_df[self.settings_df['variable'] == f'second_shot_gap'].reset_index().at[0, vac])
            params_template['vaccine_settings'][vac]['max_second_shot_delay'] = int(self.settings_df[self.settings_df['variable'] == f'max_second_shot_delay'].reset_index().at[0, vac])
            # print('Level 1a')

            epoch_length = int(self.duration + params_template['vaccine_settings'][vac]['second_shot_gap'] + params_template['vaccine_settings'][vac]['max_second_shot_delay'])
            # print('Level 1b')

            params_template['vaccine_settings'][vac]['supply_scenario'] = self.supply_scenario_name
            params_template['vaccine_settings'][vac]['booking_limit_stretch'] = params_template['vaccine_settings'][vac]['max_second_shot_delay']
            # print('Level 1c')

            try:
                params_template['vaccine_settings'][vac]['appt_book']['first_dose']['vc'] = (appt_book_df[f'{vac}_first_dose'] * computed_vals[vac]['vc_part']).astype('int64').tolist() + ([0] * (epoch_length-len(appt_book_df)))
                params_template['vaccine_settings'][vac]['appt_book']['first_dose']['poly'] = (appt_book_df[f'{vac}_first_dose'] * computed_vals[vac]['poly_part']).astype('int64').tolist() + ([0] * (epoch_length-len(appt_book_df)))
                params_template['vaccine_settings'][vac]['appt_book']['first_dose']['mobile'] = [0] * epoch_length
                # print('Level 1d')

                params_template['vaccine_settings'][vac]['appt_book']['second_dose']['vc'] = (appt_book_df[f'{vac}_second_dose'] * computed_vals[vac]['vc_part']).astype('int64').tolist() + ([0] * (epoch_length-len(appt_book_df)))
                params_template['vaccine_settings'][vac]['appt_book']['second_dose']['poly'] = (appt_book_df[f'{vac}_second_dose'] * computed_vals[vac]['poly_part']).astype('int64').tolist() + ([0] * (epoch_length-len(appt_book_df)))
                params_template['vaccine_settings'][vac]['appt_book']['second_dose']['mobile'] = [0] * epoch_length
                # print('Level 1e')

                params_template['vaccine_settings'][vac]['location']['vc'] = [computed_vals[vac]['num_vc']] * epoch_length
                params_template['vaccine_settings'][vac]['location']['poly'] = [computed_vals[vac]['num_poly']] * epoch_length
                params_template['vaccine_settings'][vac]['location']['mobile'] = [0] * epoch_length

            except Exception as e:
                traceback.print_exc()
                raise e

        # print('Level 2')


        scenario_list = []

        policy_params = deepcopy(params_template)

        policy_params['name'] = self.scenario_name + f"_BL-{policy_params['booking_limits_solver']}_INV-{policy_params['invitation_gen_solver']}_Risk-{policy_params['risk']//7}W_Strategy-{policy_params['booking_limit_strategy']}_W-{policy_params['tput_weight']}_Pref-{policy_params['utility']['vaccine_bias']['vaccine']}{int(policy_params['utility']['vaccine_bias']['bias']*100)}"

        for vac in vaccine_types:
            epoch_length = self.duration + policy_params['vaccine_settings'][vac]['second_shot_gap'] + policy_params['vaccine_settings'][vac]['max_second_shot_delay']

            if policy_params['booking_limits_solver'] == 'None':
                policy_params['vaccine_settings'][vac]['first_dose_booking_limit'] = manual_policy_df[f'{vac}_first_dose_booking_limit'].tolist() + ([0] * (epoch_length-len(manual_policy_df)))
                policy_params['vaccine_settings'][vac]['second_dose_booking_limit'] = ([0] * policy_params['vaccine_settings'][vac]['second_shot_gap']) + manual_policy_df[f'{vac}_first_dose_booking_limit'].tolist() + ([0] * policy_params['vaccine_settings'][vac]['max_second_shot_delay'])
            else:
                policy_params['vaccine_settings'][vac]['first_dose_booking_limit'] = [0] * epoch_length
                policy_params['vaccine_settings'][vac]['second_dose_booking_limit'] = [0] * epoch_length

        if policy_params['invitation_gen_solver'] == 'None':
            policy_params['invitation'] = manual_policy_df['planned_invitation'].tolist()
        else:
            policy_params['invitation'] = [0] * self.duration

        # print('Level 3')

        with open(self.inputs_dir_path + f"/scenario/{policy_params['name']}.json", 'w+') as gen_params_file:
            json.dump({
                policy_params['name']: policy_params,
            }, gen_params_file, indent=4)
        scenario_list.append(policy_params['name'])



        return scenario_list

    def run_all(self):
        self.run_simulation()
        self.run_confidence()

    def parallel_simulation(self, scenario):

        print(scenario)
        simulator = VaccineSimulator(self.params_dict[scenario])
        person_rank, occupancy = simulator.simulate()
        result = simulator.save()

    def run_simulation(self):
        p = Pool(1)

        with p:
            p.map(self.parallel_simulation, self.scenario_list)


    def parallel_confidence(self, vaccine):

        sup = SupplyExpiry(self.supply_scenario_name)
        sup.get_confidence_trace(self.start_date, self.duration, vaccine)

    def run_confidence(self):
        p = Pool(1)

        new_vaccine_list = vaccine_types.copy()
        new_vaccine_list.append('All')

        sup = SupplyExpiry(self.supply_scenario_name)
        for vac in new_vaccine_list:
            sup.remove_confidence_trace(vac)

        with p:
            p.map(self.parallel_confidence, new_vaccine_list)
