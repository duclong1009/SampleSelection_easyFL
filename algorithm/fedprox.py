"""
This is a non-official implementation of 'Federated Optimization in Heterogeneous
Networks' (http://arxiv.org/abs/1812.06127)
"""
from .fedbase import BasicServer, BasicClient
import copy
import torch
from utils import fmodule

class Server(BasicServer):
    def __init__(self, option, model, clients, test_data = None,device='cpu'):
        super(Server, self).__init__(option, model, clients, test_data,device)
        self.init_algo_para({'mu':0.1})

class Client(BasicClient):
    @fmodule.with_multi_gpus
    def train(self, model):
        # global parameters
        src_model = copy.deepcopy(model)
        src_model.freeze_grad()
        model.train()
        optimizer = self.calculator.get_optimizer(model, lr=self.learning_rate, weight_decay=self.weight_decay, momentum=self.momentum)
        for iter in range(self.num_steps):
            # get a batch of data
            batch_data = self.get_batch_data()
            model.zero_grad()
            # calculate the loss of the model on batched dataset through task-specified calculator
            loss = self.calculator.train_one_step(model, batch_data)['loss']
            loss_proximal = 0
            for pm, ps in zip(model.parameters(), src_model.parameters()):
                loss_proximal += torch.sum(torch.pow(pm - ps, 2))
            loss = loss + 0.5 * self.mu * loss_proximal
            loss.backward()
            optimizer.step()
        return

