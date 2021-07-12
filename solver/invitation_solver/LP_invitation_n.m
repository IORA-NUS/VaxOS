function [nv] = LP_invitation_n(w, x1, x2,  K, I, s, mu, x_lb1, x_lb2)


    rN = sum(x1) + sum(x2) - sum(x_lb1) - sum(x_lb2);

    size_d = size(mu);
    dd = size_d(1);

    T = (K-1)*I + dd;


    for i = 1:K
        ii = num2str(i);
        eval(['Cn' ii ' = zeros(dd, T);']);
        eval(['Cn' ii '(1:dd, 1+I*(i-1):dd+I*(i-1)) = eye(dd);']);
    end


    ph= sdpvar(T,1);
    psi  = sdpvar(T,1);
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


    F = [A'*ph >= s*Cn'*mu - x1(1:T) + x_lb1(1:T), B'*ph >= 0];
    F = [F, A'*psi >= (1-s)*Cn'*mu - x2(1:T) + x_lb2(1:T), B'*psi >= 0];
    F = [F, ones(K,1)'*n == rN, n(:) >= 0];


    obj = ph'*b + psi'*b;

    ops = sdpsettings('solver','mosek');
    optimize(F, obj, ops);
    nv = double(n);

    disp('Objective:')
    disp(value(obj));

end
