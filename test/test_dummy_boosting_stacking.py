"""
test one instance of SimDeep
"""

from os.path import abspath
from os.path import split

from os.path import isfile
from os.path import isdir

from os import remove
from shutil import rmtree



def test_instance():
    """
    test stacked of SimDeepBoosting
    """
    from simdeep.simdeep_boosting import SimDeepBoosting

    PATH_DATA = '{0}/../examples/data/'.format(split(abspath(__file__))[0])

    TRAINING_TSV = {'RNA': 'rna_dummy.tsv', 'METH': 'meth_dummy.tsv'}
    SURVIVAL_TSV = 'survival_dummy.tsv'

    PROJECT_NAME = 'stacked_TestProject'
    EPOCHS = 10
    SEED = 3
    nb_it = 5
    nb_threads = 2

    boosting = SimDeepBoosting(
        # stack_multi_omic=True,
        nb_threads=nb_threads,
        nb_it=nb_it,
        split_n_fold=3,
        survival_tsv=SURVIVAL_TSV,
        training_tsv=TRAINING_TSV,
        path_data=PATH_DATA,
        project_name=PROJECT_NAME,
        path_results=PATH_DATA,
        epochs=EPOCHS,
        # normalization={'TRAIN_CORR_REDUCTION':True},
        seed=SEED)

    boosting.fit()
    boosting.predict_labels_on_full_dataset()
    boosting.compute_clusters_consistency_for_full_labels()
    boosting.evalutate_cluster_performance()
    boosting.collect_cindex_for_test_fold()
    boosting.collect_cindex_for_full_dataset()

    boosting.compute_feature_scores_per_cluster()
    boosting.write_feature_score_per_cluster()

    boosting.load_new_test_dataset(
        {'METH': 'meth_dummy.tsv'},
        'survival_dummy.tsv',
        'dummy',
        # normalization={'TRAIN_NORM_SCALE':True},
    )

    boosting.predict_labels_on_test_dataset()
    boosting.compute_c_indexes_for_test_dataset()
    boosting.compute_clusters_consistency_for_test_labels()

    from glob import glob

    for fil in glob('{0}/{1}*'.format(PATH_DATA, PROJECT_NAME)):
        if isfile(fil):
            remove(fil)
        elif isdir(fil):
            rmtree(fil)


if __name__ == '__main__':
    test_instance()
