
import numpy as np
np.set_printoptions(precision=6, suppress=True)
from scipy.stats import gaussian_kde, norm
from datetime import date, timedelta
import matplotlib.pyplot as plt

class TemporalWalker:
    """
    Helper class to generate temporal random walks on the input user-trips matrix.
    The matrix gets shape: [day, hour, origin, destination]
    Parameters
    -----------
    edges: edges [[d, i, j]], shape: samples x 3
    edges_times: real time of edges [time], shape: samples x 1
    """

    def __init__(self, n_nodes, edges, t_end,
                 scale=0.1, rw_len=4, batch_size=8,
                 init_walk_method='uniform', isTeleport=False, isJump=False,
                 ):
        if edges.shape[1] != 4: raise Exception('edges must have shape: samples x 4')

        self.n_nodes = n_nodes
        self.t_end = t_end
        self.edges_days = edges[:, [0]]
        self.edges = edges[:, [1, 2]]
        self.edges_times = edges[:, [3]]
        self.rw_len = rw_len
        self.batch_size = batch_size
        # self.loc = loc
        self.scale = scale
        self.init_walk_method = init_walk_method
        self.isTeleport = isTeleport
        self.isJump = isJump

        # # kernel density estimation around current time
        # e_t_dict = {}
        # for i in range(len(self.edges)):
        #     e = list(self.edges[i, ])

    def walk(self):
        while True:
            yield temporal_random_walk(
                self.n_nodes, self.edges_days, self.edges, self.edges_times, self.t_end,
                self.scale, self.rw_len, self.batch_size,
                self.init_walk_method, self.isTeleport, self.isJump,
            )

# @jit(nopython=True)
def temporal_random_walk(n_nodes, edges_days, edges, edges_times, t_end,
                         scale, rw_len, batch_size,
                         init_walk_method, isTeleport, isJump
                         ):
    unique_days = np.unique(edges_days.reshape(1, -1)[0])
    walks = []

    for _ in range(batch_size):
        while True:
            # select a day with uniform distribution
            walk_day = np.random.choice(unique_days)
            mask = edges_days.reshape(1, -1)[0] == walk_day
            # subset for this day
            walk_day_edges = edges[mask]
            walk_day_times = edges_times[mask]

            # select a start edge. and unbiased or biased to the starting edges
            n = walk_day_edges.shape[0]
            if n >= rw_len: break

        n = n - rw_len + 1
        if init_walk_method is 'uniform': probs = Uniform_Prob(n)
        elif init_walk_method is 'linear': probs = Linear_Prob(n)
        elif init_walk_method is 'exp': probs = Exp_Prob(n)
        else: raise Exception('wrong init_walk_method!')

        if n == 1: start_walk_inx = 0
        else: start_walk_inx = np.random.choice(n, p=probs)

        # choice nodes from start to walker lengths. if isTeleport: sample by the teleport probability
        # which allow sample a nearby nodes based on a small random teleport
        if isTeleport:
            # selected_walks = np.apply_along_axis(
            #     func1d=lambda x: np.random.choice(n_nodes, p=teleport_probs[x[0]]),
            #     axis=1,
            #     arr=selected_walks,
            # )
            raise Exception('isTeleport not implemented yet')
        else:
            selected_walks = walk_day_edges[start_walk_inx:start_walk_inx + rw_len]
            selected_times = walk_day_times[start_walk_inx:start_walk_inx + rw_len]
        if isJump:
            raise Exception('isJump not implemented yet')

        # get start residual time
        if start_walk_inx == 0: t_res_0 = t_end
        else:
            # print('selected start:', selected_walks[0])
            t_res_0 = t_end - walk_day_times[start_walk_inx-1, 0]

        # convert to residual time
        selected_times = t_end - selected_times

        # # convert to edge index
        # selected_walks = [nodes_to_edge(e[0], e[1], n_nodes) for e in selected_walks]

        # add a stop sign of -1
        x = 1
        if start_walk_inx > 0: x = 0
        walks_mat = np.c_[selected_walks, selected_times]
        if rw_len > len(selected_walks):
            n_stops = rw_len - len(selected_walks)
            walks_mat = np.r_[walks_mat, [[-1, -1, -1]] * n_stops]

        # add start resdidual time
        if start_walk_inx == n-1:
            is_end = 1.
        else:
            is_end = 0.
        walks_mat = np.r_[[[x] + [is_end] + [t_res_0]], walks_mat]

        walks.append(walks_mat)
    return np.array(walks)

def nodes_to_edge(v, u, N):
    return v * N + u

def edge_to_nodes(e, N):
    return (e // N, e % N)

def Split_Train_Test(edges, train_ratio):
    days = sorted(np.unique(edges[:, 0]))
    b = days[int(train_ratio*len(days))]
    train_mask = edges[:, 0] <= b
    train_edges = edges[train_mask]
    test_edges = edges[ ~ train_mask]
    return train_edges, test_edges

def KDE(data):
    kernel = gaussian_kde(dataset=data, bw_method='silverman')
    return kernel

def Sample_Posterior_KDE(kernel, loc, scale, n):
    points = []
    n1 = 100
    for i in range(n):
        new_data = np.random.normal(loc, scale, n1)
        prior_probs = norm.pdf((new_data - loc) / scale)
        gau_probs = kernel.pdf(new_data)
        new_data_probs = prior_probs * gau_probs
        selected = np.random.choice(n1, p=new_data_probs / new_data_probs.sum())
        points.append(new_data[selected])
    return np.array(points)

def Exp_Prob(n):
    # n is the total number of edges
    if n == 1: return [1.]
    c = 1. / np.arange(1, n + 1, dtype=np.int)
    #     c = np.cbrt(1. / np.arange(1, n+1, dtype=np.int))
    exp_c = np.exp(c)
    return exp_c / exp_c.sum()

def Linear_Prob(n):
    # n is the total number of edges
    if n == 1: return [1.]
    c = np.arange(n+1, 1, dtype=np.int)
    return c / c.sum()

def Uniform_Prob(n):
    # n is the total number of edges
    if n == 1: return [1.]
    c = [1./n]
    return c * n


def Distance(a, b):
    return np.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


# def Teleport():
    # metro_stations = gpd.read_file('data/metro/metro-stations-regional-correct.geojson')
    # n = metro_stations.shape[0]
    # metro_stations['STATION'] = metro_stations['STATION'] - 1
    # distance_matrix = np.zeros((91, 91), dtype=np.float)
    # for i in range(n):
    #     i_id = metro_stations['STATION'][i]
    #     i_geom = metro_stations.geometry[i]
    #     for j in range(i + 1, n):
    #         j_id = metro_stations['STATION'][j]
    #         j_geom = metro_stations.geometry[j]
    #         # 0.02 degree is about 1 km
    #         distance_matrix[i_id, j_id] = 0.1 if Distance(i_geom, j_geom) < 0.02 else 0.001
    #
    # distance_matrix = distance_matrix + distance_matrix.T
    # np.fill_diagonal(distance_matrix, 1)
    # # distance_matrix = np.exp(distance_matrix)
    #
    # teleport_probs = distance_matrix / distance_matrix.sum(axis=1).reshape(-1, 1)
    #
    # return teleport_probs


def Get_Weekday(day):
    start_day = date(2016, 5, 1)
    current_day = start_day + timedelta(day)
    return current_day.weekday()


def Is_Weekend(day):
    w = Get_Weekday(day)
    return w in [0, 6]

def get_edge_times(data):
    edge_dict = {}
    for i, j, t in data[:, 1:]:
        edge = (int(i), int(j))
        if edge in edge_dict: edge_dict[edge] = edge_dict[edge] + [t]
        else: edge_dict[edge] = [t]
    return edge_dict

def plot_edge_time_hist(edge_dict, t0, tmax, bins, ymax, save_file=None, show=True):
    edges = list(edge_dict.keys())
    n_fig = len(edges)
    hight = n_fig * 2
    fig, ax = plt.subplots(n_fig, 1, figsize=(12, hight))
    for i in range(n_fig):
        e = edges[i]
        ax[i].hist(edge_dict[e], range=[t0, tmax], bins=bins)
        ax[i].set_ylim(0, ymax)
        ax[i].set_title('edge {}'.format(e))
        if i < n_fig-1: ax[i].set_xticklabels([])
    if save_file: plt.savefig(save_file)
    if show: plt.show()

def convert_graphs(fake_graphs):
    _, _, e, k = fake_graphs.shape
    fake_graphs = fake_graphs.reshape([-1, e, k])
    tmp_list = None
    for d in range(fake_graphs.shape[0]):
        d_graph = fake_graphs[d]
        d_graph = d_graph[d_graph[:, 2] > 0.]
        d_graph = np.c_[np.array([[d]] * d_graph.shape[0]), d_graph]
        if tmp_list is None:
            tmp_list = d_graph
        else:
            tmp_list = np.r_[tmp_list, d_graph]
    return tmp_list

if __name__ == '__main__':

    # scale = 0.1
    # rw_len = 2
    # batch_size = 8
    # train_ratio = 0.9
    #
    # # random data from metro
    # file = 'data/auth_user_0.txt'
    # edges = np.loadtxt(file)
    # n_nodes = int(edges[:, 1:3].max() + 1)
    # print(edges)
    # print('n_nodes', n_nodes)
    # t_end = 1.
    # train_edges, test_edges = Split_Train_Test(edges, train_ratio)
    # # print('train shape:', train_edges.shape)
    # # print('test shape:', test_edges.shape)
    # walker = TemporalWalker(n_nodes, train_edges, t_end,
    #                         scale, rw_len, batch_size,
    #                         init_walk_method='uniform',
    #                         )
    #
    # walks = walker.walk().__next__()
    # print('walk length:', rw_len)
    # print('walks shape:\n', walks.shape)
    # print('walks:\n', walks)

    # _it = '20191231-204105_assembled_graph_iter_30000'
    # fake_file = './outputs-auth-user-0-best/{}.npz'.format(_it)
    # res = np.load(fake_file)
    # fake_graphs = res['fake_graphs'][:2]
    # fake_graphs = convert_graphs(fake_graphs)
    # print('fake_graphs', fake_graphs.shape)
    # print(fake_graphs)
    # real_walks = res['fake_graphs']
    # np.savez_compressed(fake_file, fake_graphs=fake_graphs, real_walks=real_walks)

    _it = '20200129-001952_assembled_graph_iter_2'
    fake_file = './outputs-nodes-10-samples-1000/{}.npz'.format(_it)
    res = np.load(fake_file)
    fake_graphs = res['fake_graphs']
    print('fake_graphs', fake_graphs[fake_graphs[:, 0] < 3])

    print()