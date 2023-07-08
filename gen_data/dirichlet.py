import numpy as np
import random
import time



def iid_divide(l, g):
    """
    https://github.com/TalwalkarLab/leaf/blob/master/data/utils/sample.py
    divide list l among g groups
    each group has either int(len(l)/g) or int(len(l)/g)+1 elements
    returns a list of groups
    """
    num_elems = len(l)
    group_size = int(len(l) / g)
    num_big_groups = num_elems - g * group_size
    num_small_groups = g - num_big_groups
    glist = []
    for i in range(num_small_groups):
        glist.append(l[group_size * i: group_size * (i + 1)])
    bi = group_size * num_small_groups
    group_size += 1
    for i in range(num_big_groups):
        glist.append(l[bi + group_size * i:bi + group_size * (i + 1)])
    return glist


def split_list_by_indices(l, indices):
    """
    divide list l given indices into len(indices) sub-lists
    sub-list i starts from indices[i] and stops at indices[i+1]
    returns a list of sub-lists
    """
    res = []
    current_index = 0
    for index in indices:
        res.append(l[current_index: index])
        current_index = index

    return res


def by_labels_non_iid_split(dataset, n_classes, n_clients, n_clusters, alpha, frac=1, seed=1234):
    """
    split classification dataset among n_clients. The dataset is split as follow:
        1) classes are grouped into n_clusters
        2) for each cluster c, samples are partitioned across clients using dirichlet distribution

    Inspired by the split in "Federated Learning with Matched Averaging"__(https://arxiv.org/abs/2002.06440)

    :param dataset:
    :type dataset: torch.utils.Dataset
    :param n_classes: number of classes present in dataset
    :param n_clients: number of clients
    :param n_clusters: number of clusters to consider; if it is -1, then n_clusters = n_classes
    :param alpha: parameter controlling the diversity among clients
    :param frac: fraction of dataset to use
    :param seed:
    :return: list (size n_clients) of subgroups, each subgroup is a list of indices.
    """
    key = True
    rng_seed = (seed if (seed is not None and seed >= 0) else int(time.time()))
    rng = random.Random(rng_seed)
    np.random.seed(rng_seed)
    # get subset
    n_samples = int(len(dataset) * frac)
    print("Number samples: ", n_samples)
    # selected_indices = np.random.randint(0, len(dataset), n_samples)
    selected_indices = np.random.choice(range(len(dataset)), n_samples, replace=False)
    while(key):

        if n_clusters == -1:
            n_clusters = n_classes

        
        all_labels = list(range(n_classes))
        rng.shuffle(all_labels)
        clusters_labels = iid_divide(all_labels, n_clusters)

        label2cluster = dict()  # maps label to its cluster
        for group_idx, labels in enumerate(clusters_labels):
            for label in labels:
                label2cluster[label] = group_idx
        
        clusters_sizes = np.zeros(n_clusters, dtype=int)
        clusters = {k: [] for k in range(n_clusters)}
        for idx in selected_indices:
            label = dataset[idx][1]
            group_id = label2cluster[label]
            clusters_sizes[group_id] += 1
            clusters[group_id].append(idx)

        for _, cluster in clusters.items():
            rng.shuffle(cluster)

        clients_indices = [[] for _ in range(n_clients)]    
        clients_counts = np.zeros((n_clusters, n_clients), dtype=np.int64)  # number of samples by client from each cluster
        
        for cluster_id in range(n_clusters):
                weights = np.random.dirichlet(alpha=alpha * np.ones(n_clients))
                clients_counts[cluster_id] = np.random.multinomial(clusters_sizes[cluster_id], weights)
        # breakpoint()
        if np.where( clients_counts.sum(0) ==0)[0].shape[0] == 0:
            key = False
        else: 
            # print("Re run")
            continue
        clients_counts = np.cumsum(clients_counts, axis=1)

        for cluster_id in range(n_clusters):
            cluster_split = split_list_by_indices(clusters[cluster_id], clients_counts[cluster_id])

            for client_id, indices in enumerate(cluster_split):
                clients_indices[client_id] += indices

        return clients_indices

import json
with open("pill_dataset/medium_pilldataset/train_dataset_samples.json", "r") as f:
    samples = json.load(f)['samples']


import pandas as pd
def sta(client_dict,labels):
    rs = []
    for client in range(100):
        tmp = []
        for i in range(150):
            tmp.append(sum(labels[j][1] == i for j in client_dict[client]))
        rs.append(tmp)
    df = pd.DataFrame(rs,columns=[f"Label_{i}" for i in range(150)])
    return df  

n_client =100
n_cluster = 20
n_class = 150
alpha = 0.01
seed = 1234
fraction = 1

# with open("pill_dataset/medium_pilldataset/categories.json", "r") as f:
#     categories = json.load(f)

# hash_dict = {}
# count = 0
# clean_data = []
# for key in categories.keys():
#     label = int(key)
#     list_clean = categories[key]['clean']
#     for id in list_clean:
#         hash_dict[count] = id
#         count +=1 
#         clean_data.append([count, label])
with open("pill_dataset/medium_pilldataset/train_dataset_samples.json", "r") as f:
    data = json.load(f)['samples']

client_idx = by_labels_non_iid_split(data, n_class, n_client, n_cluster, alpha,fraction,seed)
client_samples_idx = {}
# for i in range(n_client):
#     client_samples_idx[i] = [int(hash_dict[tmp]) for tmp in client_idx[i]]
for i in range(n_client):
    client_samples_idx[i] = [int(tmp) for tmp in client_idx[i]]
foloder_path = f"pill_dataset/medium_pilldataset/{n_client}client/dirichlet"
import os

if not os.path.exists(foloder_path):
    os.makedirs(foloder_path)

with open(f"{foloder_path}/data_idx_alpha_{alpha}_cluster_{n_cluster}.json","w") as f:
    json.dump(client_samples_idx,f)

config = {"n_clients":n_client,
          "n_clusters":n_cluster,
          "alpha": alpha,
          "seed": seed,
          "fraction": fraction}

with open(f"{foloder_path}/data_idx_alpha_{alpha}_cluster_{n_cluster}_config.json","w") as f:
    json.dump(config,f)

df = sta(client_samples_idx,samples)
df.to_csv(f"{foloder_path}/data_idx_alpha_{alpha}_cluster_{n_cluster}_stat.csv")
# breakpoint()
# by_labels_non_iid_split()