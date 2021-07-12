function [nv] = LP_invitation_n_t(w, x, K, I, mu, x_lb)


rN = sum(x) - sum(x_lb);


size_d = size(mu);
dd = size_d(1);

T = (K-1)*I + dd;

 
 for i = 1:K
     ii = num2str(i);
    eval(['Cn' ii ' = zeros(dd, T)']);
    eval(['Cn' ii '(1:dd, 1+I*(i-1):dd+I*(i-1)) = eye(dd)']);
 end


ph= sdpvar(T,1);
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
eval(['Cn = Cn + Cn' num2str(i) '*n(i)']);
end
       

F = [A'*ph >= Cn'*mu - x(1:T) + x_lb(1:T), B'*ph >= 0];
F = [F, ones(K,1)'*n == rN, n(:) >= 0];


obj = ph'*b;

ops = sdpsettings('solver','mosek');
optimize(F, obj, ops);
nv = double(n);    


end
