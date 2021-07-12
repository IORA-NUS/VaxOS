
function  [xv, yv] = booking_limits_solver_lp(T, lt, bt, N, su, sl, c, mu, x_lb, safety)
    % T: Time Horizon, int
    % lt: Lead time between Vaccine 1 and 2, int
    % bt: Bffer time for 2nd dose, int
    % N: Total Demand, int
    % su: Vaccine Supply Arrival, int array
    % sl: Vaccien Supply Expiry, int array
    % c: capacity, int array
    % mu: mean demand, int array
    % safety: Days of safety stock reservation, int
    % x_lb: Lowerbound for 1st Dose Booking limits (init conditions), int array

    mu = mu';
    % mu = [N; zeros(T-1, 1)];
    c = c';
    x_lb = x_lb'; % ensure dimensions are correct

    disp(T)
    disp(lt)
    disp(bt)
    disp(N)
    disp(su)
    disp(sl)
    disp(c)
    disp(mu)
    disp(x_lb)
    disp(safety)

    Ty = T+lt+bt; % dimension of x and y

    Su = zeros(Ty,1);
    Su(1) = su(1);
    for i = 1:Ty-1
        Su(i+1) = Su(i)+su(i+1);
    end
    disp(Su)

    Sl = zeros(Ty,1);
    Sl(1) = sl(1);
    for i = 1:Ty-1
        Sl(i+1) = Sl(i)+sl(i+1);
    end
    % disp(Sl)

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

    C5 = zeros(Ty, Ty);
    for i = 1:Ty-safety
        C5(i, i+1: i+safety) = 1;

    end

    for i = Ty - safety + 1: Ty
        C5(i, i+1:Ty) = 1;
    end

    A = -eye(T);
    B = -eye(T);
    b = -ones(T,1);
    for i = 1 : T-1
        A(i, i+1) = 1;
    end

    ph = sdpvar(T,1);
    x = sdpvar(Ty,1);
    y = sdpvar(Ty, 1);
    z = sdpvar(T*Ty, 1);
    v = sdpvar(Ty,1);

    F = [A'*ph >= mu(1:T) - x(1:T), x(T+1:Ty) == 0, B'*ph >= 0];
    F = [F, x + y <= c, C1z*z == 0, C2z*z + C2x*x == 0, C3z*z + C3y*y == 0];
    F = [F, C4*x + C4*y + C5*y + C4*v <= Su, C4*x + C4*y + C5*y + C4*v >= Sl];
    F = [F, x(:)>=0, y(:)>=0, z(:)>=0, v(:)>=0];
    F = [F, x >= x_lb];

    obj = ph'*b;

    ops = sdpsettings('solver','mosek');
    % ops = sdpsettings('solver','glpk');
    % [model,recoverymodel] = export(F, obj, ops);

    % disp(model)
    % disp('_______________________________________________')
    % disp(recoverymodel)
    % disp('_______________________________________________')

    % saveampl(F,obj,'bookinglimits.ampl');

    diagnostics = optimize(F, obj, ops);
    % disp(diagnostics.solverinput);


    %WT = double(obj);
    xv = double(x);
    yv  = double(y);
   % z_v = double(z);
   % Z = zeros(T, Ty);
    %for i = 1:T
   %     for j = 1:Ty
    %        Z(i,j) = z_v(Ty*(i-1)+j);
   %     end

    disp('Objective:')
    disp(value(obj));

    end


