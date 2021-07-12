t0 = cputime;

T =60;
lt = 21; %two shots lead time
bt = 4; %beyond time
Ty = T+lt+bt; % dimension of x and y
Su_LT = 14; % supply lead time
Sl_LT = 20;  % expiry period
%current practice
rp= 0.53;

N =[ 1100 * rp; 2500* rp];

% Evenly staggered
% B3 = 361;
% B4 = 638;
% B5 = 360;
% B6 = 90;
% B7 = 2515;
% N = [(B3+B4)*0.5, (B5+B6)*rp1, B7*rp2]';
[mu, cov] = demand_gen(T, N);
Sigma = mu*mu' + cov;

su = zeros(Ty,1);
su(1: Su_LT: Ty) = sum(N)/2;
Su = zeros(Ty,1);
Su(1) = su(1);
for i = 1:Ty-1
    Su(i+1) = Su(i)+su(i+1);
end

sl= zeros(Ty,1);
sl(Sl_LT:Su_LT: Ty) = sum(N)/2; 
 
 Sl = zeros(Ty,1);
Sl(1) = sl(1);
for i = 1:Ty-1
    Sl(i+1) = Sl(i)+sl(i+1);
end
 plot((1:1:Ty), Su, (1:1:Ty), Sl);
c = 84*ones(Ty, 1);


C1z = eye(T*Ty);
for i = 1:T
        C1z(((i-1)*Ty +lt+i:(i-1)*Ty +lt+bt+i), ((i-1)*Ty +lt+i:(i-1)*Ty +lt+bt+i)) = 0;
end

C2z = zeros(T, T*Ty);
for i = 1: T
     for j = 1:Ty
        C2z(i, (i-1)*Ty +j) = 1;
     end
end

C2x = zeros(T, Ty);
C2x(1:T, 1:T) = - eye(T);


C3z = zeros(Ty, T*Ty);
for i = 1: Ty
     for j = 1:T
        C3z(i,(j-1)*Ty+i) = 1;
     end
end

C3y = -eye(Ty);

C4 = tril(ones(Ty, Ty));



rho  = sdpvar(1,1);
nu  = sdpvar(T,1);
ph = sdpvar(T,1);
gam = sdpvar(T,1);
Th  = sdpvar(T,T);
M  = sdpvar(1+3*T,1+3*T);
N  = sdpvar(1+3*T,1+3*T);
x = sdpvar(Ty,1);
y = sdpvar(Ty, 1);
z = sdpvar(T*Ty, 1);
v = sdpvar(Ty,1);

A = -eye(T);
B = -eye(T);
b = -ones(T,1);
for i = 1 : T-1
    A(i, i+1) = 1;
end
COP = [rho        nu'/2            ph'*[A B]/2 
       nu/2         Th             zeros(T, 2*T)
       [A B]'*ph/2  zeros(2*T, T) [A B]'*diag(gam)*[A B]];
 COP = COP  - [ 0              zeros(1, T)     -x(1:T)'/2   zeros(1,T)
       zeros(1, T)'   zeros(T,T)       eye(T)/2    zeros(T, T)
       -x(1:T)/2           eye(T)/2              zeros(T, 2*T)
       zeros(T, 1+3*T)];
      
       
F = [COP == M + N, M(:) >= 0, N>=0];
F = [F, x(T+1:Ty) == 0, x + y <= c, C1z*z == 0, C2z*z + C2x*x == 0];
F = [F, x(:)>=0, y(:)>=0, z(:)>=0, v(:)>=0];
F = [F, C3z*z + C3y*y == 0, C4*x + C4*y + C4*v <= Su, C4*x + C4*y + C4*v >= Sl];

obj = rho + nu'*mu + trace(Th*Sigma)+ph'*b + (b.*b)'*gam;
 

ops = sdpsettings('solver','mosek');
optimize(F, obj, ops);
    

COP_v = double(COP);
WT = double(obj);
x_v = double(x);
ax = 1:1:Ty;
yv  = double(y);
plot(ax, x_v, ax, double(y))
z_v = double(z);
Z = zeros(T, Ty);
for i = 1:T
    for j = 1:Ty
        Z(i,j) = z_v(Ty*(i-1)+j);
    end
end
hold off
com_time = cputime - t0;