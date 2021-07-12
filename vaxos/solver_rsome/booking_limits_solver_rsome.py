import os
import numpy as np
from datetime import datetime

from rsome import ro            # Import the ro modeling tool
from rsome import lpg_solver as lpg
# from rsome import ort_solver as ort
from rsome import msk_solver as msk


from vaxos.supply_expiry import SupplyExpiry
from vaxos.params import Params, location_types
from vaxos.custom_dist import CustomDist

_DEBUG = False

class BookingLimitsSolver_RSome:

    def __init__(self, params, vaccine, request_time=datetime.now()):
        self.params = params
        self.request_time = request_time
        # self.d_type = "4"
        self.dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.log_path = os.path.dirname(os.path.realpath(__file__)) + '/archive/log'
        os.makedirs(self.log_path, exist_ok=True)

        self.model = ro.Model('Booking Limits Solver')    # Create a Model object

        planning_duration = self.params['planning_duration'] if self.params.get('planning_duration') is not None else self.params['duration']

        # self.T = self.params['duration']
        self.T = planning_duration
        self.lt = self.params['vaccine_settings'][vaccine]['second_shot_gap']
        self.bt = self.params['vaccine_settings'][vaccine]['booking_limit_stretch']

        supply_expiry = SupplyExpiry(self.params['vaccine_settings'][vaccine]['supply_scenario'])
        # self.Ty = self.params['duration'] + self.params['vaccine_settings'][vaccine]['second_shot_gap'] + self.params['vaccine_settings'][vaccine]['booking_limit_stretch']
        self.Ty = planning_duration + self.params['vaccine_settings'][vaccine]['second_shot_gap'] + self.params['vaccine_settings'][vaccine]['booking_limit_stretch']
        # print(self.Ty)

        # su = supply_expiry.get_supply_vector(self.params['start_date'], Ty, state="Supply", vaccine=vaccine, cumulative=False, include_init=False)
        self.su = supply_expiry.get_supply_at_confidence_level(self.params['start_date'], self.Ty, vaccine, ptile=self.params['vaccine_settings'][vaccine].get('supply_confidence'))

        self.su = [max(0, s) for s in self.su]
        # su = supply_expiry.get_supply_vector(self.params['start_date'], Ty, state="Supply", vaccine=vaccine, cumulative=False, include_init=True)
        self.sl = [0] * self.Ty
        self.N = sum(self.su)/2

        self.c = [0] * self.Ty
        for loc in location_types:
            if len(self.params['vaccine_settings'][vaccine]['location'][loc]) < self.Ty:
                val = self.params['vaccine_settings'][vaccine]['location'][loc][-1]
                qty = self.Ty - len(self.params['vaccine_settings'][vaccine]['location'][loc])
                self.params['vaccine_settings'][vaccine]['location'][loc].extend([val] * qty)
            self.c = np.add(self.c, self.params['capacity'][loc] * np.array(self.params['vaccine_settings'][vaccine]['location'][loc][:self.Ty]))
        self.c = self.c.tolist()

        last_val = self.c[-1]
        for i in range(len(self.c), self.Ty):
            self.c.extend([last_val])

        # distribution_mean = custom_dist[f"{self.params['distribution']}_mean"]
        # distribution_sd = custom_dist[f"{self.params['distribution']}_sd"]
        distribution_mean = CustomDist(self.params['distribution']).mean()
        distribution_sd = CustomDist(self.params['distribution']).sd()

        self.mu = [0] * self.Ty # self.params['duration']

        for i in range(len(distribution_mean)):
            self.mu[i] = int(distribution_mean[i] * self.N)

        self.x_lb, _, _ = Params.get_appt_book(self.params, vaccine)
        self.x_lb = self.x_lb + ([0] * (self.Ty-len(self.x_lb)) )
        # print(x_lb)
        # safety=self.params['saftey_reservation']
        risk = self.params['vaccine_settings'][vaccine].get('risk', self.params['risk'])
        # self.safety=max(0, self.params['vaccine_settings'][vaccine]['second_shot_gap'] - self.params['risk'])
        self.safety=max(0, self.params['vaccine_settings'][vaccine]['second_shot_gap'] - risk)

        print(f'{__class__.__name__} {vaccine} Inputs:')
        print(f"T: {self.T}")
        print(f"lt: {self.lt}")
        print(f"bt: {self.bt}")
        print(f"N: {self.N}")
        print(f"su: {self.su}")
        print(f"sl: {self.sl}")
        print(f"c: {self.c}")
        print(f"mu: {self.mu}")
        print(f"x_lb: {self.x_lb}")
        print(f"safety: {self.safety}")

        # self.mu = np.transpose(np.array(self.mu))
        self.mu = np.array(self.mu).reshape(self.Ty,1)
        self.c = np.array(self.c).reshape(self.Ty,1)
        self.x_lb = np.array(self.x_lb).reshape(self.Ty,1)

    def solve(self):

        # Cumulative supply
        Su = np.zeros((self.Ty, 1))
        Su[0] = self.su[0]
        for i in range(self.Ty-1):
            Su[i+1] = Su[i] + self.su[i+1]

        # print(Su)


        # Decision variables:
        ph = self.model.dvar((self.T, 1))
        x = self.model.dvar((self.Ty, 1))
        y = self.model.dvar((self.Ty, 1))
        z = self.model.dvar((self.T * self.Ty, 1))
        v = self.model.dvar((self.Ty, 1))



        # Coefficients
        # C1z = eye(T*Ty);
        # for i = 1:T
        #         C1z(((i-1)*Ty +lt+i:(i-1)*Ty +lt+bt+i), ((i-1)*Ty +lt+i:(i-1)*Ty +lt+bt+i)) = 0;
        # end
        C1z = np.eye(self.T * self.Ty)
        for i in range(self.T):
            for p in range((i*self.Ty) + self.lt + i, (i*self.Ty) + self.lt + self.bt + i+1):
                for q in range((i*self.Ty) + self.lt + i, (i*self.Ty) + self.lt + self.bt + i+1):
                    C1z[p][q] = 0

        # C2z = zeros(T, T*Ty);
        # for i = 1: T
        #     for j = 1:Ty
        #         C2z(i, (i-1)*Ty +j) = 1;
        #     end
        # end
        C2z = np.zeros((self.T, self.T * self.Ty) )
        for i in range(self.T):
            for j in range(self.Ty):
                C2z[i][(i*self.Ty) +j] = 1

        # C2x = zeros(T, Ty);
        # C2x(1:T, 1:T) = - eye(T);
        C2x = np.zeros((self.T, self.Ty) )
        for i in range(self.T):
            C2x[i][i] = -1

        # C3z = zeros(Ty, T*Ty);
        # for i = 1: Ty
        #     for j = 1:T
        #         C3z(i,(j-1)*Ty+i) = 1;
        #     end
        # end
        C3z = np.zeros((self.Ty, self.T * self.Ty) )
        for i in range(self.Ty):
            for j in range(self.T):
                C3z[i][(j*self.Ty) + i] = 1

        # C3y = -eye(Ty);
        C3y = -np.eye(self.Ty)

        # C4 = tril(ones(Ty, Ty));
        C4 = np.tril(np.ones((self.Ty, self.Ty) ))

        # C5 = zeros(Ty, Ty);
        # for i = 1:Ty-safety
        #     C5(i, i+1: i+safety) = 1;
        C5 = np.zeros((self.Ty, self.Ty) )
        for i in range(self.Ty - self.safety):
            for p in range(i+1, i+self.safety + 1):
                C5[i][p] = 1

        # Coefficients
        A = -np.eye(self.T)
        B = -np.eye(self.T)
        b = -np.ones((self.T, 1))
        for i in range(self.T - 1):
            A[i][i+1] = 1

        # if _DEBUG:
        #     print(f'A: {A}')
        #     print(f'B: {B}')
        #     print(f'b: {b}')
        #     print('----------')

        # model
        # F = [A'*ph >= mu(1:T) - x(1:T), B'*ph >= 0];
        if _DEBUG:
            print(f'A.T: {A.T.shape}')
            print(f'ph: {ph.shape}')
            print(f'A.T @ ph: {(A.T @ ph).shape}')
            print(f'self.mu[0:self.T]: {self.mu[0:self.T].shape}')
            print(f'x[0:self.T]: {x[0:self.T].shape}')
            print('----------')
        self.model.st(A.T @ ph >= self.mu[0:self.T] - x[0:self.T])

        if _DEBUG:
            print(f'B.T: {B.T.shape}')
            print(f'ph: {ph.shape}')
            print(f'B.T @ ph: {(B.T @ ph).shape}')
            print('----------')
        self.model.st(B.T @ ph >= 0)

        # F = [F, x + y <= c, C1z*z == 0, C2z*z + C2x*x == 0, C3z*z + C3y*y == 0];
        if _DEBUG:
            print(f'x: {x.shape}')
            print(f'y: {y.shape}')
            print(f'self.c: {self.c.shape}')
            print('----------')
        self.model.st(x + y <= self.c)

        if _DEBUG:
            print(f'C1z: {C1z.shape}')
            print(f'z: {z.shape}')
            print(f'C1z @ z: {(C1z @ z).shape}')
            print('----------')
        self.model.st(C1z @ z == 0)

        if _DEBUG:
            print(f'C2z: {C2z.shape}')
            print(f'z: {z.shape}')
            print(f'C2x: {C2x.shape}')
            print(f'x: {x.shape}')
            print('----------')
        self.model.st((C2z @ z) + (C2x @ x) == 0)

        if _DEBUG:
            print(f'C3z: {C3z.shape}')
            print(f'z: {z.shape}')
            print(f'C3y: {C3y.shape}')
            print(f'y: {y.shape}')
            print('----------')
        self.model.st((C3z @ z) + (C3y @ y) == 0)

        # F = [F, C4*x + C4*y + C5*y + C4*v <= Su, C4*x + C4*y + C5*y + C4*v >= Sl];
        if _DEBUG:
            print(f'C4: {C4.shape}')
            print(f'C5: {C5.shape}')
            print(f'x: {x.shape}')
            print(f'y: {y.shape}')
            print(f'v: {v.shape}')
            print(f'Su: {Su.shape}')
            print('----------')
        self.model.st((C4 @ x) + (C4 @ y) + (C5 @ y) + (C4 @ v) <= Su)
        self.model.st((C4 @ x) + (C4 @ y) + (C5 @ y) + (C4 @ v) >= 0)

        # F = [F, x(:)>=0, y(:)>=0, z(:)>=0, v(:)>=0];
        self.model.st(x >= 0)
        self.model.st(y >= 0)
        self.model.st(z >= 0)
        self.model.st(v >= 0)

        # F = [F, x >= x_lb];
        self.model.st(x >= self.x_lb)

        # Additional Fix set x[i] = 0 for i in T..Ty
        self.model.st(x[self.T:self.Ty] == 0)

        # # objective
        # # obj = ph'*b;
        if _DEBUG:
            print(f'ph.T: {ph.T.shape}')
            print(f'b: {b.shape}')
            print('----------')
        self.model.min(ph.T @ b)

        # primal = self.model.do_math()
        # print(primal.show())

        # # # Solve
        self.model.solve(lpg)
        # self.model.solve(msk)

        print(f'Objective: {self.model.get()}')

        # print(x.get().astype('int').reshape(self.Ty).tolist(), y.get().astype('int').reshape(self.Ty).tolist())

        first_dose_booking_limit = x.get().astype('double').reshape(self.Ty).tolist()
        second_dose_booking_limit = y.get().astype('double').reshape(self.Ty).tolist()

        return [round(x) for x in first_dose_booking_limit], [round(x) for x in second_dose_booking_limit]
