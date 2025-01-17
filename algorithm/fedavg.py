from .fedbase import BasicServer, BasicClient

class Server(BasicServer):
    def __init__(self, option, model, clients, test_data = None,device='cpu'):
        super(Server, self).__init__(option, model, clients, test_data,device)

class Client(BasicClient):
    def __init__(self, option, name='', train_data=None, valid_data=None,device='cpu'):
        super(Client, self).__init__(option, name, train_data, valid_data,device)
