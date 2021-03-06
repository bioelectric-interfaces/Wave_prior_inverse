import scipy.io
import numpy as np
from sklearn import metrics
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

G_raw = scipy.io.loadmat('/home/ksasha/PycharmProjects/Wave_prior/Wave_prior_inverse/G.mat')
cortex_raw = scipy.io.loadmat('/home/ksasha/PycharmProjects/Wave_prior/Wave_prior_inverse/cortex.mat')
G = G_raw['G'][np.arange(2, 306, 3)]  # magnetometers
cortex = cortex_raw['cortex'][0]
vertices = cortex[0][1]

# wave generation parameters
params = {'duration': 0.02, 'Fs': 1000, 'speeds': [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]}

Num_sim = 2
snr = [0.1, 0.2, 0.5, 1, 2]
ntpoints = int(params['duration']*params['Fs']+1)

y_true = np.zeros(Num_sim*2)
y_true[0:Num_sim] = np.ones(Num_sim)

auc = np.zeros(len(snr))
k = 0

plt.figure()
lw = 2
plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')


for snr_level in snr:
    # wave_fit = np.zeros(2*Num_sim, dtype=int)
    speed_fit = np.zeros([len(snr), Num_sim], dtype=int)
    direction_fit = np.zeros([len(snr), Num_sim], dtype=int)
    score_fit = np.zeros(2*Num_sim)
    generate_direction = np.zeros(Num_sim, dtype=int)
    generate_speed = np.zeros(Num_sim, dtype=int)
    src_idx = np.zeros(Num_sim, dtype=int)
    brain_noise_norm = np.zeros([G.shape[0], params['Fs'], Num_sim])

    # first Nsim trials with waves
    for sim_n in range(0, Num_sim):
        src_idx[sim_n] = np.random.randint(0, G.shape[1])
        [sensor_waves, path_indices, path_final] = create_waves_on_sensors(cortex, params, G, src_idx[sim_n], spheric=0)

        generate_direction[sim_n] = np.random.randint(0, sensor_waves.shape[0])
        generate_speed[sim_n] = np.random.randint(0, sensor_waves.shape[1])

        # visualization
        # fig = plt.figure()
        # ax = fig.add_subplot(111, projection='3d')
        # ax.scatter(vertices[:,0], vertices[:,1], vertices[:,2])
        # for d in range(0, path_final.shape[0]):
        #     ax.scatter(path_final[d, 10, :, 0], path_final[d, 10, :, 1], path_final[d, 10, :, 2], marker = '^')

        brain_noise = generate_brain_noise(G)
        brain_noise_norm[:, :, sim_n] = brain_noise/np.linalg.norm(brain_noise)
        wave_picked = sensor_waves[generate_direction[sim_n], generate_speed[sim_n], :, :]
        wave_picked_norm = wave_picked/np.linalg.norm(wave_picked)
        data = snr_level*wave_picked_norm + brain_noise_norm[:, :sensor_waves.shape[3], sim_n]

        # plt.figure()
        # plt.plot(data.T)
        [score_fit[sim_n], best_coefs, best_shift, best_speed_ind] = LASSO_inverse_solve(data, sensor_waves)
        # wave_fit[sim_n] = (score_fit[sim_n] > 0.7)
        speed_fit[k, sim_n] = (best_speed_ind == generate_speed[sim_n])
        direction_fit[k, sim_n] = (np.argmax(best_coefs) == generate_direction[sim_n])
        print(sim_n)

    # next Nsim trials without waves
    for sim_n in range(Num_sim, 2*Num_sim):
        idx = src_idx[sim_n-Num_sim]
        [sensor_blob, path_indices] = create_blob_on_sensors(cortex, params, G, idx)
        [sensor_waves, path_indices, path_final] = create_waves_on_sensors(cortex, params, G, idx, spheric=0)

        brain_noise =  brain_noise_norm[:, :, sim_n-Num_sim]
        sensor_blob_norm = sensor_blob/np.linalg.norm(sensor_blob)
        data = snr_level*sensor_blob_norm + brain_noise[:, :sensor_blob.shape[1]]

        # plt.figure()
        # plt.plot(data.T)

        [score_fit[sim_n], best_coefs, best_shift, best_speed_ind] = LASSO_inverse_solve(data, sensor_waves)
        # wave_fit[sim_n] = (score_fit[sim_n] > 0.7)
        print(sim_n)


    y_score = score_fit
    fpr, tpr, thresholds = metrics.roc_curve(y_true, y_score)
    auc[k] = metrics.roc_auc_score(y_true, y_score)
    plt.plot(fpr, tpr, lw=lw, label='ROC curve for SNR {0}, (area = {1:0.2f})'.format(snr_level, auc[k]))
    k+=1

plt.title('Receiver operating characteristics for different SNR')
plt.legend(loc="lower right")
plt.show()

direction_ratio = np.zeros(len(snr))
speed_ratio = np.zeros(len(snr))
for i in range(0, len(snr)):
    direction_ratio[i] = sum(direction_fit[i])/Num_sim*100
    speed_ratio[i] = sum(speed_fit[i])/Num_sim*100

plt.figure()
plt.subplot(2,1,1)
plt.plot(snr, direction_ratio, 'o-')
plt.title('Direction detection ratio')
plt.subplot(2,1,2)
plt.plot(snr, speed_ratio, 'o-')
plt.title('Speed detection ratio')

