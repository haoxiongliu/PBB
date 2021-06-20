import math
import numpy as np
import torch
import torch.distributions as td
from tqdm.auto import tqdm, trange
import torch.nn.functional as F


class PBBobj():
    """Class including all functionalities needed to train a NN with a PAC-Bayes inspired 
    training objective and evaluate the risk certificate at the end of training. 

    Parameters
    ----------
    objective : string
        training objective to be optimised (choices are fquad, flamb, fclassic or fbbb)
        modified by haoxiong liu: add pointwise classic bound fpoint
    
    pmin : float
        minimum probability to clamp to have a loss in [0,1]

    classes : int
        number of classes in the learning problem
    
    train_size : int
        n (number of training examples)

    delta : float
        confidence value for the training objective
    
    delta_test : float
        confidence value for the chernoff bound (used when computing the risk)

    mc_samples : int
        number of Monte Carlo samples when estimating the risk

    kl_penalty : float
        penalty for the kl coefficient in the training objective
    
    device : string
        Device the code will run in (e.g. 'cuda')

    """
    def __init__(self, objective='fquad', pmin=1e-4, classes=10, train_size=50000, delta=0.025,
    delta_test=0.01, mc_samples=1000, kl_penalty=1, device='cuda'):
        super().__init__()
        self.objective = objective
        self.pmin = pmin
        self.classes = classes
        self.device = device
        self.train_size = train_size
        self.delta = delta
        self.delta_test = delta_test
        self.mc_samples = mc_samples
        self.kl_penalty = kl_penalty

    def compute_empirical_risk(self, outputs, targets, bounded=True):
        # compute negative log likelihood loss and bound it with pmin (if applicable)
        empirical_risk = F.nll_loss(outputs, targets)
        if bounded == True:
            empirical_risk = (1./(np.log(1./self.pmin))) * empirical_risk
        return empirical_risk

    def compute_losses(self, net, data, target, clamping=True, sample=True):
        # compute both cross entropy and 01 loss
        # returns outputs of the network as well
        outputs = net(data, sample=sample,
                      clamping=clamping, pmin=self.pmin)
        loss_ce = self.compute_empirical_risk(
            outputs, target, clamping)
        pred = outputs.max(1, keepdim=True)[1]
        correct = pred.eq(
            target.view_as(pred)).sum().item()
        total = target.size(0)
        loss_01 = 1-(correct/total)
        return loss_ce, loss_01, outputs

    def bound(self, empirical_risk, kl, lambda_var=None):
        # compute training objectives
        if self.objective == 'fquad':
            kl = kl * self.kl_penalty
            repeated_kl_ratio = torch.div(
                kl + np.log((2*np.sqrt(self.train_size))/self.delta), 2*self.train_size)
            first_term = torch.sqrt(
                empirical_risk + repeated_kl_ratio)
            second_term = torch.sqrt(repeated_kl_ratio)
            train_obj = torch.pow(first_term + second_term, 2)
        elif self.objective == 'flamb':
            kl = kl * self.kl_penalty
            lamb = lambda_var.lamb_scaled
            kl_term = torch.div(
                kl + np.log((2*np.sqrt(self.train_size)) / self.delta), self.train_size*lamb*(1 - lamb/2))
            first_term = torch.div(empirical_risk, 1 - lamb/2)
            train_obj = first_term + kl_term
        elif self.objective == 'fclassic' or self.objective == 'fpoint':
            kl = kl * self.kl_penalty
            kl_ratio = torch.div(
                kl + np.log((2*np.sqrt(self.train_size))/self.delta), 2*self.train_size)
            train_obj = empirical_risk + torch.sqrt(kl_ratio)
        elif self.objective == 'bbb':
            # ipdb.set_trace()
            train_obj = empirical_risk + \
                self.kl_penalty * (kl/self.train_size)
        else:
            raise RuntimeError(f'Wrong objective {self.objective}')
        return train_obj

    def empirical_risk_sample(self, net, input=None, target=None, batches=True, clamping=True, data_loader=None, sample=True):
        # compute both cross entropy and 01 loss
        # returns outputs of the network as well
        loss_ce = loss_01 = 0
        if batches:
            for batch_id, (data_batch, target_batch) in enumerate(tqdm(data_loader, position=0)):
                data_batch, target_batch = data_batch.to(
                    self.device), target_batch.to(self.device)
                cross_entropy, error, _ = self.compute_losses(net,
                                                          data_batch, target_batch, clamping, sample=sample)
                loss_ce += cross_entropy
                loss_01 += error
            # we average cross-entropy and 0-1 error over all batches
            loss_ce /= batch_id
            loss_01 /= batch_id
        else:
            loss_ce, loss_01, _ = self.compute_losses(net, input, target, clamping, sample=True)
        return loss_ce, loss_01


    def mcsampling(self, net, input, target, batches=True, clamping=True, data_loader=None):
        # compute empirical risk with Monte Carlo sampling
        error = 0.0
        cross_entropy = 0.0
        if batches:
            for batch_id, (data_batch, target_batch) in enumerate(tqdm(data_loader, position=0)):
                data_batch, target_batch = data_batch.to(
                    self.device), target_batch.to(self.device)
                cross_entropy_mc = 0.0
                error_mc = 0.0
                for i in range(self.mc_samples):
                    loss_ce, loss_01, _ = self.compute_losses(net,
                                                              data_batch, target_batch, clamping)
                    cross_entropy_mc += loss_ce
                    error_mc += loss_01
                # we average cross-entropy and 0-1 error over all MC samples
                cross_entropy += cross_entropy_mc/self.mc_samples
                error += error_mc/self.mc_samples
            # we average cross-entropy and 0-1 error over all batches
            cross_entropy /= batch_id
            error /= batch_id
        else:
            cross_entropy_mc = 0.0
            error_mc = 0.0
            for i in range(self.mc_samples):
                loss_ce, loss_01, _ = self.compute_losses(net,
                                                          input, target, clamping)
                cross_entropy_mc += loss_ce
                error_mc += loss_01
                # we average cross-entropy and 0-1 error over all MC samples
            cross_entropy += cross_entropy_mc/self.mc_samples
            error += error_mc/self.mc_samples
        return cross_entropy, error

    def train_obj(self, net, input, target, clamping=True, lambda_var=None):
        # compute train objective and return all metrics
        outputs = torch.zeros(target.size(0), self.classes).to(self.device)
        # if self.objective is not 'fpoint':
        kl = net.compute_kl()
        # else:
        #     kl = net.compute_kl_point()
        loss_ce, loss_01, outputs = self.compute_losses(net,
                                                        input, target, clamping)
        train_obj = self.bound(loss_ce, kl, lambda_var)
        return train_obj, kl/self.train_size, outputs, loss_ce, loss_01

    def compute_final_stats_risk(self, net, input=None, target=None, data_loader=None, clamping=True, lambda_var=None):
        # compute all final stats and risk certificates
        kl = net.compute_kl()

        if self.objective is 'fpoint':
            if data_loader:
                empirical_risk_ce, empirical_risk_01 = \
                    self.empirical_risk_sample(net, input, target, batches=True, clamping=True, data_loader=data_loader)
            else:
                empirical_risk_ce, empirical_risk_01 = \
                    self.empirical_risk_sample(net, input, target, batches=False, clamping=True)
        else:
            if data_loader:
                error_ce, error_01 = self.mcsampling(net, input, target, batches=True,
                                                     clamping=True, data_loader=data_loader)
            else:
                error_ce, error_01 = self.mcsampling(net, input, target, batches=False,
                                                     clamping=True)
            empirical_risk_ce = inv_kl(
                error_ce.item(), np.log(2/self.delta_test)/self.mc_samples)
            empirical_risk_01 = inv_kl(
                error_01, np.log(2/self.delta_test)/self.mc_samples)

        train_obj = self.bound(empirical_risk_ce, kl, lambda_var)

        risk_ce = inv_kl(empirical_risk_ce, (kl + np.log((2 *
                                                             np.sqrt(self.train_size))/self.delta_test))/self.train_size)
        risk_01 = inv_kl(empirical_risk_01, (kl + np.log((2 *
                                                             np.sqrt(self.train_size))/self.delta_test))/self.train_size)
        return train_obj, kl/self.train_size, empirical_risk_ce, empirical_risk_01, risk_ce, risk_01


def inv_kl(qs, ks):
    """Inversion of the binary kl

    Parameters
    ----------
    qs : float
        Empirical risk

    ks : float
        second term for the binary kl inversion

    """
    # computation of the inversion of the binary KL
    qd = 0
    ikl = 0
    izq = qs
    dch = 1-1e-10
    while((dch-izq)/dch >= 1e-5):
        p = (izq+dch)*.5
        if qs == 0:
            ikl = ks-(0+(1-qs)*math.log((1-qs)/(1-p)))
        elif qs == 1:
            ikl = ks-(qs*math.log(qs/p)+0)
        else:
            ikl = ks-(qs*math.log(qs/p)+(1-qs) * math.log((1-qs)/(1-p)))
        if ikl < 0:
            dch = p
        else:
            izq = p
        qd = p
    return qd
