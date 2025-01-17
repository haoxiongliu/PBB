import torch
from pbb.utils import runexp

if __name__ == '__main__':

    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.autograd.set_detect_anomaly(True)
    print(torch.cuda.is_available())

    BATCH_SIZE = 250
    TRAIN_EPOCHS = 10
    DELTA = 0.025
    DELTA_TEST = 0.01
    PRIOR = 'learnt'

    SIGMAPRIOR = 0.01   # also change
    PMIN = 1e-5
    KL_PENALTY = 0.1
    LEARNING_RATE = 0.001   # important
    MOMENTUM = 0.95
    LEARNING_RATE_PRIOR = 0.005
    MOMENTUM_PRIOR = 0.99

    # note the number of MC samples used in the paper is 150.000, which usually takes a several hours to compute
    MC_SAMPLES = 1000

    runexp('cifar10', 'fpoint', 'learnt', 'cnn', SIGMAPRIOR, PMIN, LEARNING_RATE, MOMENTUM, LEARNING_RATE_PRIOR, MOMENTUM_PRIOR,
           delta=DELTA, delta_test=DELTA_TEST, mc_samples=MC_SAMPLES, train_epochs=10, device=DEVICE,
           prior_epochs=20, perc_train=1.0, perc_prior=0.7, verbose=False, dropout_prob=0.2, layers=9)

    # note all of these running examples have different settings!
    # runexp('mnist', 'fquad', 'rand', 'fcn', SIGMAPRIOR, PMIN, LEARNING_RATE, MOMENTUM, LEARNING_RATE_PRIOR, MOMENTUM_PRIOR, delta=DELTA, delta_test=DELTA_TEST, mc_samples=MC_SAMPLES, train_epochs=TRAIN_EPOCHS, device=DEVICE, perc_train=1.0, verbose=True, dropout_prob=0.2)

    # runexp('mnist', 'flamb', PRIOR, 'fcn', SIGMAPRIOR, PMIN, LEARNING_RATE, MOMENTUM, LEARNING_RATE_PRIOR, MOMENTUM_PRIOR, delta=DELTA, delta_test=DELTA_TEST, mc_samples=MC_SAMPLES, train_epochs=TRAIN_EPOCHS, device=DEVICE, prior_epochs=70, perc_train=1.0, perc_prior=0.5, verbose=True, dropout_prob=0.2)

    # runexp('mnist', 'fclassic', 'learnt', 'cnn', SIGMAPRIOR, PMIN, LEARNING_RATE, MOMENTUM, LEARNING_RATE_PRIOR, MOMENTUM_PRIOR, delta=DELTA, delta_test=DELTA_TEST, mc_samples=MC_SAMPLES, train_epochs=TRAIN_EPOCHS, device=DEVICE, prior_epochs=70, perc_train=1.0, perc_prior=0.5, verbose=False, dropout_prob=0.2)

    # runexp('cifar-10', 'bbb', PRIOR, 'cnn', SIGMAPRIOR, PMIN, LEARNING_RATE, MOMENTUM, LEARNING_RATE_PRIOR, MOMENTUM_PRIOR, delta=DELTA, delta_test=DELTA_TEST, mc_samples=MC_SAMPLES, train_epochs=TRAIN_EPOCHS, device=DEVICE, prior_epochs=70, perc_train=1.0, perc_prior=0.5, verbose=False, dropout_prob=0.2, kl_penalty=0.1, layers=9)
    # runexp('cifar10', 'fclassic', 'learnt', 'cnn', SIGMAPRIOR, PMIN, LEARNING_RATE, MOMENTUM, LEARNING_RATE_PRIOR, MOMENTUM_PRIOR, delta=DELTA, delta_test=DELTA_TEST, mc_samples=MC_SAMPLES, train_epochs=TRAIN_EPOCHS, device=DEVICE, prior_epochs=70, perc_train=1.0, perc_prior=0.7, verbose=False, dropout_prob=0.2, kl_penalty=0.1, layers=13)

    # new point-wise bound update
