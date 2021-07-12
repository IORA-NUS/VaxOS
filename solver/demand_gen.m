function  [mu, cov] = demand_gen(T, N)


mu = zeros(T, 1);
d_std = zeros(T, 1);

% current policyn April, invite the 45-59 yrs first to make bookings. 
% There will be estimated 585k regimens, but 1.1 mil 
% individuals aged 45-59 yrs invited.
% 
% About two weeks later, we will invite the rest of Singapore 
% (est. 2.5 mil pax) to make bookings. 
% 
% Supply for rest of April dependent on take-up for 45-59 yrs. 

n_g = 2;
lam = 4;

prob = zeros(n_g, T);
prob (1, :) = poisspdf(0:T-1, lam)*N(1);
prob (2, 15:T) = poisspdf(0:T-15, lam)*N(2);


   

% Evenly staggering

% size_N = size(N);
% n_g = size_N(1);
% prob = zeros(n_g, T);
% 
% lam = 4;
% for i  =  1: n_g
%     prob(i, ((i-1)*ceil(T/n_g)+1):T) = poisspdf(0:T-(i-1)*ceil(T/n_g)-1,lam)*N(i);
% end

for i = 1:T
    mu(i)  = sum(prob(:, i));
    for j = 1:n_g   
    d_std(i) = sqrt(d_std(i)^2 + (prob(j, i)/N(j))*(1-prob(j,i)/N(j))*N(j));
    end
end
     


at= (1:1:T);

plot(at, mu)
errorbar(at, mu, d_std)
hold on
cov = diag(d_std.^2);
end




%    
