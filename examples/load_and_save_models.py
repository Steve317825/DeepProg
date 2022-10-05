import os
os.environ['PYTHONHASHSEED']=str(2020)

import random
random.seed(2020)

from os.path import abspath
from os.path import split

from simdeep.simdeep_boosting import SimDeepBoosting
from simdeep.simdeep_utils import save_model
from simdeep.simdeep_utils import load_model


def test_instance():
    """
    example of SimDeepBoosting
    """
    PATH_DATA = '{0}/../examples/data/'.format(split(abspath(__file__))[0])

    #Input file
    TRAINING_TSV = {'RNA': 'rna_dummy.tsv', 'METH': 'meth_dummy.tsv'}
    SURVIVAL_TSV = 'survival_dummy.tsv'

    PROJECT_NAME = 'TestProject'
    SEED = 3
    nb_it = 2 # Number of models to be built
    nb_threads = 2 # Number of processes to be used to fit individual survival models

    ################ AUTOENCODER PARAMETERS ################
    EPOCHS = 10
    ## Additional parameters for the autoencoders can be defined, see config.py file for details
    # LEVEL_DIMS_IN = [250]
    # LEVEL_DIMS_OUT = [250]
    # LOSS = 'binary_crossentropy'
    # OPTIMIZER = 'adam'
    # ACT_REG = 0
    # W_REG = 0
    # DROPOUT = 0.5
    # DATA_SPLIT = 0
    # ACTIVATION = 'tanh'
    #########################################################

    ################ ADDITIONAL PARAMETERS ##################
    # PATH_TO_SAVE_MODEL = '/home/username/deepprog'
    # PVALUE_THRESHOLD = 0.01
    # NB_SELECTED_FEATURES = 10
    # STACK_MULTI_OMIC = False
    #########################################################

    from sklearn.preprocessing import RobustScaler
    norm = {
            'CUSTOM': RobustScaler,
    }

    boosting = SimDeepBoosting(
        nb_threads=nb_threads,
        nb_it=nb_it,
        split_n_fold=3,
        survival_tsv=SURVIVAL_TSV,
        training_tsv=TRAINING_TSV,
        path_data=PATH_DATA,
        project_name=PROJECT_NAME,
        path_results=PATH_DATA,
        epochs=EPOCHS,
        seed=SEED,
        normalization=norm,
        cluster_method='mixture',
        use_autoencoders=True,
        feature_surv_analysis=True,
        distribute=False
        # stack_multi_omic=STACK_MULTI_OMIC,
        # level_dims_in=LEVEL_DIMS_IN,
        # level_dims_out=LEVEL_DIMS_OUT,
        # loss=LOSS,
        # optimizer=OPTIMIZER,
        # act_reg=ACT_REG,
        # w_reg=W_REG,
        # dropout=DROPOUT,
        # data_split=DATA_SPLIT,
        # activation=ACTIVATION,
        # path_to_save_model=PATH_TO_SAVE_MODEL,
        # pvalue_threshold=PVALUE_THRESHOLD,
        # nb_selected_features=NB_SELECTED_FEATURES,
    )

    boosting.fit()
    save_model(boosting, "./test_saved_model")

    del boosting

    boosting = load_model("TestProject", "./test_saved_model")

    boosting.predict_labels_on_full_dataset()

    boosting.compute_clusters_consistency_for_full_labels()
    boosting.evalutate_cluster_performance()
    boosting.collect_cindex_for_test_fold()
    boosting.collect_cindex_for_full_dataset()

    boosting.compute_feature_scores_per_cluster()
    boosting.write_feature_score_per_cluster()
    boosting.collect_number_of_features_per_omic()
    boosting.compute_pvalue_for_merged_test_fold()

    boosting.load_new_test_dataset(
        {'RNA': 'rna_dummy.tsv'}, # OMIC file of the test set. It doesnt have to be the same as for training
        'dummy', # Name of the test test to be used
        'survival_dummy.tsv', # Survival file of the test set Optional
    )

    boosting.predict_labels_on_test_dataset()
    boosting.compute_c_indexes_for_test_dataset()
    boosting.compute_clusters_consistency_for_test_labels()

    boosting.load_new_test_dataset(
        {'METH': 'meth_dummy.tsv'}, # OMIC file of the second test set.
        'dummy_METH', # Name of the second test test
        'survival_dummy.tsv', # Survival file of the test set Optional
    )

    boosting.predict_labels_on_test_dataset()
    boosting.compute_c_indexes_for_test_dataset()
    boosting.compute_clusters_consistency_for_test_labels()


if __name__ == '__main__':
    test_instance()
