from benchmark.toolkits import CustomDataset
from .fedbase import BasicServer, BasicClient
import importlib
import utils.fflow as flw
import utils.fmodule
import copy
import torch.nn as nn
import numpy as np
import os
from torch.utils.data import DataLoader
import math
import torch

class Server(BasicServer):
    def __init__(self, option, model, clients, test_data = None,device='cpu'):
        super(Server, self).__init__(option, model, clients, test_data,device)
        self.sampler = utils.fmodule.Sampler
        self.threshold_score = 0

        #init goodness_cached
        self.goodness_cached = {}
        self.saved_histogram = {}
        for _ in range(len(clients)):
            self.goodness_cached[_] = 0
            # self.saved_histogram[_] = []
        self.score_range = 0
        self.max_score = 0

    def iterate(self):
        """
        The standard iteration of each federated round that contains three
        necessary procedure in FL: client selection, communication and model aggregation.
        :param
            t: the number of current round
        """
        # sample clients: MD sampling as default
        self.selected_clients = self.sample()
        utils.fmodule.LOG_DICT["selectd_client"] = self.selected_clients
        flw.logger.info(f"Selected clients : {self.selected_clients}")
        f"Total samples which participate training :{sum([self.local_data_vols[i] for i in self.selected_clients])} samples"
        global current_round
        current_round = self.current_round
        # training
        models = self.communicate(self.selected_clients)["model"]
        # aggregate: pk = 1/K as default where K=len(selected_clients)
        self.model = self.aggregate(models, self.local_data_vols)
        return

class Client(BasicClient):
    def __init__(self, option, name='', train_data=None, valid_data=None,device='cpu'):
        super(Client, self).__init__(option, name, train_data, valid_data,device)


    def train(self, model):
        """
        Standard local training procedure. Train the transmitted model with local training dataset.
        :param
            model: the global model
        :return
        """
        self.calculate_importance(copy.deepcopy(model))
        
        if self.data_loader == None:
            print(f"Client {self.id} init its dataloader")
            self.data_loader = DataLoader(
                self.train_data,
                batch_size=self.batch_size,
                num_workers=self.loader_num_workers,
                shuffle=True,
            )
        model.train()
        optimizer = self.calculator.get_optimizer(
            model,
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
            momentum=self.momentum,
        )
        list_training_loss = []
        for epoch in range(self.epochs):
            training_loss = 0
            for data, labels, idxs in self.data_loader:
                data, labels = data.float().to(self.device), labels.long().to(
                    self.device
                )
                optimizer.zero_grad()
                outputs = model(data)
                torch.nn.CrossEntropyLoss(reduction="none")(outputs, labels)
                loss = self.calculator.criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                training_loss += loss.item()
            list_training_loss.append(training_loss / len(self.data_loader))

        if not "training_loss" in utils.fmodule.LOG_DICT.keys():
            utils.fmodule.LOG_DICT["training_loss"] = {}
        utils.fmodule.LOG_DICT["training_loss"][
            f"client_{self.id}"
        ] = list_training_loss
        utils.fmodule.LOG_WANDB["mean_training_loss"] = sum(list_training_loss) / len(
            list_training_loss
        )
        return

    def calculate_importance(self, model):
        criteria = nn.CrossEntropyLoss()
        _, score_list_on_cl, conf_arr = utils.fmodule.Sampler.cal_score_a_conf(
            self.train_data, model, criteria, self.device
        )
        self.score_cached = score_list_on_cl
        self.conf_arr = conf_arr
        # f'{self.option["log_result_path"]}/{self.option["group_name"]}/{self.option["session_name"]}'
        if not os.path.exists(f'{self.option["log_result_path"]}/{self.option["group_name"]}/{self.option["session_name"]}/round_{current_round}'):
            os.makedirs(f'{self.option["log_result_path"]}/{self.option["group_name"]}/{self.option["session_name"]}/round_{current_round}')
        with open(f'{self.option["log_result_path"]}/{self.option["group_name"]}/{self.option["session_name"]}/round_{current_round}/confarr_{self.name}.npy',"wb") as f:
            np.save(f,conf_arr)
