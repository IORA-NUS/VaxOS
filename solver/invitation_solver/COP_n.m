function [nv] = COP_n(w, x1, x2,  K, I, s, mu, x_lb1, x_lb2)


rN = sum(x1) + sum(x2) - sum(x_lb1) - sum(x_lb2);


size_d = size(mu);
dd = size_d(1);

T = (K-1)*I + dd;

d_std = sqrt(mu.*(1-mu));
 cov = diag(d_std.^2);
 Sigma = mu*mu' + cov;

 for i = 1:K
     ii = num2str(i);
    eval(['Cn' ii ' = zeros(dd, T);']);
    eval(['Cn' ii '(1:dd, 1+I*(i-1):dd+I*(i-1)) = eye(dd);']);
 end

rho1  = sdpvar(1,1);
nu1  = sdpvar(dd,1);
rho2  = sdpvar(1,1);
nu2  = sdpvar(dd,1);
ph1 = sdpvar(T,1);
gam1 = sdpvar(T,1);
ph2 = sdpvar(T,1);
gam2 = sdpvar(T,1);

Th1  = sdpvar(dd,dd);
Th2  = sdpvar(dd,dd);
M11  = sdpvar(1+2*T+dd,1+2*T+dd);
M12  = sdpvar(1+2*T+dd,1+2*T+dd);
M21  = sdpvar(1+2*T+dd,1+2*T+dd);
M22  = sdpvar(1+2*T+dd,1+2*T+dd);
n = sdpvar(K,1);


A = -eye(T);
B = -eye(T);
b = -(1-w)*ones(T,1);
b(T) = -1;
for i = 1 : T-1
    A(i, i+1) = 1;
end
Cn = zeros(dd, T);
for i = 1:K
eval(['Cn = Cn + Cn' num2str(i) '*n(i);']);
end
%

COP1 = [rho1        nu1'/2            ph1'*[A B]/2
       nu1/2         Th1             zeros(dd, 2*T)
       [A B]'*ph1/2  zeros(2*T, dd) [A B]'*diag(gam1)*[A B]
       ];
 COP1 = COP1  - [ 0              zeros(1, dd)     -(x1(1:T)-x_lb1(1:T))'/2      zeros(1,T)
                zeros(1, dd)'   zeros(dd,dd)     s*Cn/2   zeros(dd, T)
                -(x1(1:T)-x_lb1(1:T))/2      s*Cn'/2     zeros(T, T)    zeros(T, T)
                zeros(T, 1+2*T+dd)
       ];

 COP2 = [rho2        nu2'/2            ph2'*[A B]/2
       nu2/2         Th2             zeros(dd, 2*T)
       [A B]'*ph2/2  zeros(2*T, dd) [A B]'*diag(gam2)*[A B]
       ];
 COP2 = COP2 - [ 0              zeros(1, dd)     -(x2(1:T)-x_lb2(1:T))'/2      zeros(1,T)
                zeros(1, dd)'   zeros(dd,dd)     (1-s)*Cn/2   zeros(dd, T)
                -(x2(1:T)-x_lb2(1:T))/2      (1-s)*Cn'/2     zeros(T, T)    zeros(T, T)
                zeros(T, 1+2*T+dd)
       ];

F = [COP1 == M11 + M12, M11(:) >= 0, M12 >= 0];
F = [F, COP2 == M21 + M22, M21(:) >= 0, M22 >= 0];
F = [F, ones(K,1)'*n == rN, n(:) >= 0];

obj = rho1 + nu1'*mu + trace(Th1*Sigma) + rho2 + nu2'*mu + trace(Th2*Sigma) + ph1'*b + (b.*b)'*gam1 + ph2'*b + (b.*b)'*gam2;


ops = sdpsettings('solver','mosek');
optimize(F, obj, ops);
nv = double(n);


end
