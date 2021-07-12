
%output: invitation schedule n: in the scale of 1000
%Input: 
% solv: LP model or COP model; solv = 1: LP; solv = 0: COP
% fs: the flag of whether run invitaiton schedule considering split or w/o considering split between two vaccines. fs = 1: with split; fs = 0: without split
% s: split ratio between Pfizer and Moderna. e.g. s= 0.6: Pfizer split 60% of total population
% mu: demand arrival pattern in terms of probability
% x1: first dose booking limit of Pfizer
% x2: first dose booking limit of Modena 
% Note that x1 and x2 are of the same dimention;
% K: Number of waves 
% I : Invitation interval, e.g., I = 14 for biweekly invitation
% rp: response rate
function [n] = invitation(solv, fs, s, mu, x1, x2, K, I, rp, x_lb1, x_lb2, w)
 % weight on unused booking slots. w =1 corresponds to Most aggressive schedule 
size_d = size(mu);
dd = size_d(1);
T = (K-1)*I + dd;

% check the dimension of x1, x2. need to larger than T. 
size_x1 = size(x1);
dx1 = size_x1(1);
size_x2 = size(x2);
dx2 = size_x2(1);
if T >= dx1   
x1p = zeros(T,1);
x1p(1:dx1) = x1;
x1 = x1p;
end
if T >= dx2
x2p = zeros(T,2);
x2p(1:dx2) = x2;
x2 = x2p;
end
% rescale x1 x2 as in the scale of 1000.
x1 = x1/1000;
x2 = x2/1000;
x_lb1 = x_lb1/1000;
x_lb2 = x_lb2/1000;

if solv == 0
    if fs == 1
    [nv] = COP_n(w, x1, x2,  K, I, s, mu, x_lb1, x_lb2);
    end
    if fs == 0
    [nv] = COP_n_t(w, x1+x2, K, I, mu, x_lb1+x_lb2);
    end
end
if solv == 1
   if fs == 1
    [nv] = LP_invitation_n(w, x1, x2,  K, I, s, mu, x_lb1, x_lb2);
   end
    if fs == 0
    [nv] = LP_invitation_n_t(w, x1+x2, K, I, mu, x_lb1+x_lb2);
    end 
end
n = nv/rp;
end
