import os
import numpy as np
from datetime import datetime

from rsome import ro            # Import the ro modeling tool
from rsome import lpg_solver as lpg
# from rsome import ort_solver as ort
# from rsome import msk_solver as msk


from vaxos.supply_expiry import SupplyExpiry
from vaxos.params import Params, location_types, vaccine_types
from vaxos.custom_dist import CustomDist

_DEBUG = True

class InvitationWavesSolver_RSome:

    def __init__(self, params, request_time=datetime.now()):
        self.params = params
        self.request_time = request_time
        # self.d_type = "4"
        self.dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.log_path = os.path.dirname(os.path.realpath(__file__)) + '/archive/log'
        os.makedirs(self.log_path, exist_ok=True)

        planning_duration = self.params['planning_duration'] if self.params.get('planning_duration') is not None else self.params['duration']

        self.model = ro.Model('Invitation Waves Solver')    # Create a Model object

        self.w = 1 if self.params.get('tput_weight') is None else self.params.get('tput_weight')

        if self.params['invitation_gen_solver'] == 'lp':
            self.solv = 1
            self.mock = False
        elif self.params['invitation_gen_solver'] == 'cop':
            raise Exception("invitation_gen_solver: 'cop' is not supported in this version")
        #     self.solv = 0
        #     self.mock = False
        else:
            self.solv = 1 # value does not matter
            self.mock = True

        # Only Pfizer Bias  is allowed
        if self.params['utility']['vaccine_bias']['vaccine'] == 'Pfizer':
            self.fs = 1
            self.s = self.params['utility']['vaccine_bias']['bias']
        else:
            self.fs = 0
            self.s = 0

        # mu = custom_dist[f"{self.params['distribution']}_mean"]
        custom_dist = CustomDist(self.params['distribution'])
        self.mu = custom_dist.mean()

        longest_epoch = 0
        # x_lb = [0] * self.params['duration']
        for vac in vaccine_types:
            # if longest_epoch < self.params['duration'] + self.params['vaccine_settings'][vac]['second_shot_gap'] + self.params['vaccine_settings'][vac]['max_second_shot_delay']:
            #     longest_epoch = self.params['duration'] + self.params['vaccine_settings'][vac]['second_shot_gap'] + self.params['vaccine_settings'][vac]['max_second_shot_delay']
            if longest_epoch < planning_duration + self.params['vaccine_settings'][vac]['second_shot_gap'] + self.params['vaccine_settings'][vac]['max_second_shot_delay']:
                longest_epoch = planning_duration + self.params['vaccine_settings'][vac]['second_shot_gap'] + self.params['vaccine_settings'][vac]['max_second_shot_delay']

        self.Ty = longest_epoch

        #     first_dose, _, _ = Params.get_appt_book(self.params, vac)
        #     x_lb = np.add(x_lb, first_dose[:self.params['duration']])

        # x_lb = x_lb.tolist()

        self.x_lb1, _, _ = Params.get_appt_book(self.params, 'Pfizer')
        self.x_lb1 = self.x_lb1 +  ([0]* (longest_epoch - len(self.x_lb1)))

        self.x_lb2, _, _ = Params.get_appt_book(self.params, 'Moderna')
        self.x_lb2 = self.x_lb2 +  ([0]* (longest_epoch - len(self.x_lb2)))


        self.x1 = self.params['vaccine_settings']['Pfizer']['first_dose_booking_limit'] + ([0]* (longest_epoch - len(self.params['vaccine_settings']['Pfizer']['first_dose_booking_limit'])))
        self.x2 = self.params['vaccine_settings']['Moderna']['first_dose_booking_limit'] + ([0]* (longest_epoch - len(self.params['vaccine_settings']['Moderna']['first_dose_booking_limit'])))


        # self.K = int(self.params['duration'] / self.params['invitation_frequency'])
        self.K = int(planning_duration / self.params['invitation_frequency'])
        # K=1
        self.I = self.params['invitation_frequency']
        self.rp = self.params['plan_response_rate']


        print(f'{__class__.__name__} Inputs:')
        print(f"solv: {self.solv}")
        print(f"w: {self.w}")
        print(f"fs: {self.fs}")
        print(f"s: {self.s}")
        print(f"K: {self.K}")
        print(f"I: {self.I}")
        print(f"rp: {self.rp}")
        print(f"mu: {self.mu}")
        print(f"x1: {self.x1}")
        print(f"x2: {self.x2}")
        print(f"x_lb1: {self.x_lb1}")
        print(f"x_lb2: {self.x_lb2}")


        # self.mu = np.transpose(np.array(self.mu))
        self.mu = np.array(self.mu).reshape(len(self.mu),1)
        self.x1 = np.array(self.x1).reshape(self.Ty,1)
        self.x2 = np.array(self.x2).reshape(self.Ty,1)
        self.x_lb1 = np.array(self.x_lb1).reshape(self.Ty,1)
        self.x_lb2 = np.array(self.x_lb2).reshape(self.Ty,1)

    def solve(self):

        if self.mock == True:
            val = (sum(self.x1)+sum(self.x2))/self.K
            return [val] * self.K

        dd = len(self.mu)
        T = ((self.K - 1) * self.I) + len(self.mu)

        rN = sum(self.x1) + sum(self.x2) - sum(self.x_lb1) - sum(self.x_lb2)


        # Decision Variables
        # ph= sdpvar(T,1);
        # psi  = sdpvar(T,1);
        # n = sdpvar(K,1);
        ph = self.model.dvar((T, 1))
        n = self.model.dvar((self.K, 1))

        if self.fs == 1:
            psi = self.model.dvar((T, 1))



        # Coefficients
        # for i = 1:K
        #     ii = num2str(i);
        #     eval(['Cn' ii ' = zeros(dd, T)']);
        #     eval(['Cn' ii '(1:dd, 1+I*(i-1):dd+I*(i-1)) = eye(dd)']);
        # end
        Cn_wave = [[]] * self.K
        for i in range(self.K):
            Cn_wave[i] = np.zeros((dd, T))
            idx_p=0
            for p in range(dd):
                idx_q=0
                for q in range(self.I * (i), dd + (self.I * (i))):
                    if idx_p == idx_q:
                        Cn_wave[i][p][q] = 1
                    idx_q += 1
                idx_q=0
                idx_p += 1

        # Cn = zeros(dd, T);
        # for i = 1:K
        #     eval(['Cn = Cn + Cn' num2str(i) '*n(i)']);
        # end
        Cn = np.zeros((dd, T))
        for i in range(self.K):
            Cn = Cn + (Cn_wave[i] * n[i])

        # A = -eye(T);
        # B = -eye(T);
        # b = -(1-w)*ones(T,1);
        # b(T) = -1;
        # for i = 1 : T-1
        #     A(i, i+1) = 1;
        # end
        A = -np.eye(T)
        for i in range(T-1):
            A[i][i+1] = 1

        B = -np.eye(T)

        b = -(1-self.w)*np.ones((T,1))
        b[-1] = -1

        # model
        # F = [A'*ph >= s*Cn'*mu - x1(1:T) + x_lb1(1:T), B'*ph >= 0];
        # F = [A'*ph >= Cn'*mu - x(1:T) + x_lb(1:T), B'*ph >= 0];

        if _DEBUG:
            print(f'A.T: {A.T.shape}')
            print(f'ph: {ph.shape}')
            print(f'Cn.T: {Cn.T.shape}')
            print(f'self.mu: {self.mu.shape}')
            print(f'self.x1[0:T]: {self.x1[0:T].shape}')
            print(f'self.x_lb1[0:T]: {self.x_lb1[0:T].shape}')
            print(f'self.x2[0:T]: {self.x2[0:T].shape}')
            print(f'self.x_lb2[0:T]: {self.x_lb2[0:T].shape}')
            print('----------')
        if self.fs == 1:
            self.model.st(A.T @ ph >= (self.s * (Cn.T @ self.mu)) - self.x1[0:T] + self.x_lb1[0:T])
        else:
            self.model.st(A.T @ ph >= (Cn.T @ self.mu) - self.x1[0:T] - self.x2[0:T] + self.x_lb1[0:T] + self.x_lb2[0:T])

        if _DEBUG:
            print(f'B.T: {B.T.shape}')
            print(f'ph: {ph.shape}')
            print(f'B.T @ ph: {(B.T @ ph).shape}')
            print('----------')
        self.model.st(B.T @ ph >= 0)

        if self.fs == 1:
            # F = [F, A'*psi >= (1-s)*Cn'*mu - x2(1:T) + x_lb2(1:T), B'*psi >= 0];
            if _DEBUG:
                print(f'A.T: {A.T.shape}')
                print(f'psi: {psi.shape}')
                print(f'Cn.T: {Cn.T.shape}')
                print(f'self.mu: {self.mu.shape}')
                print(f'self.x2[0:T]: {self.x2[0:T].shape}')
                print(f'self.x_lb2[0:T]: {self.x_lb2[0:T].shape}')
                print('----------')
            self.model.st(A.T @ ph >= ((1-self.s) * (Cn.T @ self.mu)) - self.x2[0:T] + self.x_lb2[0:T])

            if _DEBUG:
                print(f'B.T: {B.T.shape}')
                print(f'psi: {psi.shape}')
                print(f'B.T @ psi: {(B.T @ psi).shape}')
                print('----------')
            self.model.st(B.T @ psi >= 0)


        # F = [F, ones(K,1)'*n == rN, n(:) >= 0];

        if _DEBUG:
            print(f'np.ones((self.K,1)).T: {np.ones((self.K,1)).T.shape}')
            print(f'n: {n.shape}')
            print('----------')
        self.model.st(np.ones((self.K,1)).T @ n == rN)

        self.model.st(n >= 0)

        # # objective
        # obj = ph'*b + psi'*b;
        if _DEBUG:
            print(f'ph.T: {ph.T.shape}')
            if self.fs == 1:
                print(f'psi.T: {psi.T.shape}')
            print(f'b: {b.shape}')
            print('----------')
        if self.fs == 1:
            self.model.min((ph.T @ b) + (psi.T @ b))
        else:
            self.model.min(ph.T @ b)

        # primal = self.model.do_math()
        # print(primal.show())

        # # # Solve
        self.model.solve(lpg)

        # print(n.get().astype('int').reshape(self.K).tolist())
        invitations = n.get().astype('double').reshape(self.K)
        # print(invitation.tolist())

        print(f'Objective: {self.model.get()}')

        return [round(x/self.rp) for x in invitations]
