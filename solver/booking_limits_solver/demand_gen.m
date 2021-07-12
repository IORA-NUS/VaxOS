function  [mu, cov, d_std] = demand_gen(T, N)

    mu = zeros(T, 1);
    d_std = zeros(T, 1);

    size_N = size(N);
    n_g = size_N(1);
    T0 = T;
    % demand arrival generator
    mup = 6.3;
    sigp =0.85;
    pd = makedist('Lognormal','mu',mup,'sigma',sigp);
    tpd =  truncate(pd,1,45*40+1);

    xp = (1:1:45*40+1)';
    yp = pdf(tpd,xp);


    zp = zeros(T0,1);
    for i = 1:45
        zp(i) = yp(40*(i)+1)*40;
    end


    prob = zeros(n_g, T0);
    prob (1, :) = zp'*N(1);
    %prob (2, 15:T0) = zp(1:T0-14)'*N(2);
    %prob (3, 29:T0) = zp(1:T0-28)'*N(3);

    for i = 1:T
        mu(i)  = sum(prob(:, i));
        for j = 1:n_g
        d_std(i) = sqrt(d_std(i)^2+(prob(j,i)/N(j))*(1-prob(j,i)/N(j))*N(j));
        end
    end



    at= (1:1:T);

    % plot(at, mu)
    % errorbar(at, mu, d_std)
    cov = diag(d_std.^2);
end




%
