""" """
from sklearn.preprocessing import Normalizer
from sklearn.preprocessing import RobustScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import quantile_transform

from simdeep.config import TRAINING_TSV
from simdeep.config import SURVIVAL_TSV

from simdeep.config import TEST_TSV
from simdeep.config import SURVIVAL_TSV_TEST

from simdeep.config import PATH_DATA
from simdeep.config import STACK_MULTI_OMIC

from simdeep.config import NORMALIZATION

from simdeep.config import FILL_UNKOWN_FEATURE_WITH_0

from simdeep.config import CROSS_VALIDATION_INSTANCE
from simdeep.config import TEST_FOLD

from simdeep.config import SURVIVAL_FLAG

from simdeep.survival_utils import load_data_from_tsv
from simdeep.survival_utils import load_survival_file
from simdeep.survival_utils import return_intersection_indexes
from simdeep.survival_utils import translate_index
from simdeep.survival_utils import MadScaler
from simdeep.survival_utils import RankNorm
from simdeep.survival_utils import CorrelationReducer
from simdeep.survival_utils import VarianceReducer
from simdeep.survival_utils import SampleReducer
from simdeep.survival_utils import convert_metadata_frame_to_matrix

from simdeep.survival_utils import save_matrix

from collections import defaultdict

from os.path import isfile

from time import time

import numpy as np

import pandas as pd

from numpy import hstack
from numpy import vstack


######################## VARIABLE ############################
QUANTILE_OPTION = {'n_quantiles': 100,
                   'output_distribution':'normal'}
###############################################################


class LoadData():
    """
    """

    def __init__(
            self,
            path_data=PATH_DATA,
            training_tsv=TRAINING_TSV,
            survival_tsv=SURVIVAL_TSV,
            metadata_tsv=None,
            metadata_test_tsv=None,
            test_tsv=TEST_TSV,
            survival_tsv_test=SURVIVAL_TSV_TEST,
            cross_validation_instance=CROSS_VALIDATION_INSTANCE,
            test_fold=TEST_FOLD,
            stack_multi_omic=STACK_MULTI_OMIC,
            fill_unkown_feature_with_0=FILL_UNKOWN_FEATURE_WITH_0,
            normalization=NORMALIZATION,
            survival_flag=SURVIVAL_FLAG,
            subset_training_with_meta={},
            _autoencoder_parameters={},
            verbose=True,
    ):
        """
        class to extract data
        :training_matrices: dict(matrice_type, path to the tsv file)

        :path_data: str    path to the folder containing the data
        :training_tsv: dict    dict('data type', 'name of the tsv file')
        :survival_tsv: str    name of the tsv file containing the survival data
                              of the training set
        :survival_tsv_test: str    name of the tsv file containing the survival data
                                   of the test set
        :metadata_tsv: str         name of the file containing metadata
        :metadata_test_tsv: str         name of the file containing metadata of the test set
        :tsv_test: str    name of the file containing the test dataset
        :data_type_test: str    name of the data type of the test set
                                must match a key existing in training_tsv
        """

        self.verbose = verbose
        self.do_stack_multi_omic = stack_multi_omic
        self.path_data = path_data
        self.survival_tsv = survival_tsv
        self.metadata_tsv = metadata_tsv
        self.training_tsv = training_tsv
        self.fill_unkown_feature_with_0 = fill_unkown_feature_with_0
        self.survival_flag = survival_flag
        self.feature_array = {}
        self.matrix_array = {}
        self.subset_training_with_meta = subset_training_with_meta

        self.test_tsv = test_tsv
        self.matrix_train_array = {}

        self.sample_ids = []
        self.data_type = list(training_tsv.keys())

        self.survival = None
        self.survival_tsv_test = survival_tsv_test
        self.metadata_test_tsv = metadata_test_tsv

        self.matrix_full_array = {}
        self.sample_ids_full = []
        self.survival_full = None

        self.feature_test_array = {}
        self.matrix_test_array = {}

        self.sample_ids_cv = []
        self.matrix_cv_array = {}
        self.matrix_cv_unormalized_array = {}
        self.survival_cv = None

        self._cv_loaded = False
        self._full_loaded = False

        self.matrix_ref_array = {}
        self.feature_ref_array = {}
        self.feature_ref_index = {}
        self.feature_train_array = {}
        self.feature_train_index = {}

        self.metadata_frame_full = None
        self.metadata_frame_cv = None
        self.metadata_frame_test = None
        self.metadata_frame = None

        self.metadata_mat_full = None
        self.metadata_mat_cv = None
        self.metadata_mat_test = None
        self.metadata_mat = None

        self.survival_test = None
        self.sample_ids_test = None

        self.cross_validation_instance = cross_validation_instance
        self.test_fold = test_fold

        self.do_feature_reduction = None

        self.normalizer = Normalizer()
        self.mad_scaler = MadScaler()
        self.robust_scaler = RobustScaler()
        self.min_max_scaler = MinMaxScaler()
        self.dim_reducer = CorrelationReducer()
        self.variance_reducer = VarianceReducer()

        self._autoencoder_parameters = _autoencoder_parameters
        self.normalization = defaultdict(bool, normalization)
        self.normalization_test = None

    def __del__(self):
        """
        """
        try:
            import gc
            gc.collect()
        except Exception:
               pass

    def _stack_multiomics(self, arrays=None, features=None):
        """
        """
#         print(self.do_stack_multi_omic)
        if not self.do_stack_multi_omic:
            return

        if arrays is not None:
            arrays['STACKED'] = hstack(
                tuple(arrays.values()))

            for key in list(arrays.keys()):
                arrays.pop(key) if key != 'STACKED' else True

        if not features:
            return

        features['STACKED'] = [feat for key in features
                               for feat in features[key]]
        for key in list(features.keys()):
            features.pop(key) if key != 'STACKED' else True
#         print(features.keys())
        self.feature_ref_index['STACKED'] = {feature: pos for pos, feature
                                             in enumerate(features['STACKED'])}

    def load_matrix_test_fold(self):
        """ """
        if not self.cross_validation_instance or self._cv_loaded:
            return

        for key in self.matrix_array:

            matrix_test = self.matrix_cv_array[key].copy()
            matrix_ref = self.matrix_array[key].copy()

            matrix_ref, matrix_test = self.transform_matrices(
                matrix_ref, matrix_test, key,
            )

            self.matrix_cv_unormalized_array[key] = \
                self.matrix_cv_array[key].copy()
            self.matrix_cv_array[key] = matrix_test

        self._stack_multiomics(self.matrix_cv_array)
        self._cv_loaded = True

    def load_matrix_test(self, normalization=None):
        """ """
        if normalization is not None:
            self.normalization_test = normalization
        else:
            self.normalization_test = self.normalization

        for key in self.test_tsv:
            sample_ids, feature_ids, matrix = load_data_from_tsv(
                f_name=self.test_tsv[key],
                key=key,
                path_data=self.path_data)

            feature_ids_ref = self.feature_array[key]
            matrix_ref = self.matrix_array[key].copy()

            common_features = set(feature_ids).intersection(feature_ids_ref)

            if self.verbose:
                print('nb common features for the test set:{0}'.format(len(common_features)))

            feature_ids_dict = {feat: i for i,feat in enumerate(feature_ids)}
            feature_ids_ref_dict = {feat: i for i,feat in enumerate(feature_ids_ref)}

            if len(common_features) < len(feature_ids_ref) and self.fill_unkown_feature_with_0:
                missing_features = set(feature_ids_ref).difference(common_features)

                if self.verbose:
                    print('filling {0} with 0 for {1} additional features'.format(
                        key, len(missing_features)))

                matrix = hstack([matrix, np.zeros((len(sample_ids), len(missing_features)))])

                for i, feat in enumerate(missing_features):
                    feature_ids_dict[feat] = i + len(feature_ids)

                common_features = feature_ids_ref

            feature_index = [feature_ids_dict[feature] for feature in common_features]
            feature_ref_index = [feature_ids_ref_dict[feature] for feature in common_features]

            matrix_test = np.nan_to_num(matrix.T[feature_index].T)
            matrix_ref = np.nan_to_num(matrix_ref.T[feature_ref_index].T)

            self.feature_test_array[key] = list(common_features)

            if not isinstance(self.sample_ids_test, type(None)):
                try:
                    assert(self.sample_ids_test == sample_ids)
                except Exception:
                    raise Exception('Assertion error when loading test sample ids!')
            else:
                self.sample_ids_test = sample_ids

            matrix_ref, matrix_test = self.transform_matrices(
                matrix_ref, matrix_test, key, normalization=normalization)

            self._define_test_features(key, normalization)

            self.matrix_test_array[key] = matrix_test
            self.matrix_ref_array[key] = matrix_ref
            self.feature_ref_array[key] = self.feature_test_array[key]
            self.feature_ref_index[key] = {feat: pos for pos, feat in enumerate(common_features)}

            self._define_ref_features(key, normalization)

        self._stack_multiomics(self.matrix_test_array,
                               self.feature_test_array)
        self._stack_multiomics(self.matrix_ref_array,
                               self.feature_ref_array)

    def load_meta_data_test(self, metadata_file="", sep="\t"):
        """
        """
        if metadata_file:
            self.metadata_test_tsv = metadata_file

        if isfile("{0}/{1}".format(self.path_data, self.metadata_test_tsv)):
            self.metadata_test_tsv = "{0}/{1}".format(
                self.path_data, self.metadata_test_tsv)

        if not self.metadata_test_tsv:
            return

        frame = pd.read_csv(self.metadata_test_tsv, sep=sep, index_col=0)

        diff = set(self.sample_ids_test).difference(frame.index)

        if diff:
            raise(Exception(
                "Error! samples from the tes dataset not present in metadata: {0}".format(
                    list(diff)[:5])))

        self.metadata_frame_test = frame.T[self.sample_ids_test].T
        self.metadata_mat_test = convert_metadata_frame_to_matrix(
            self.metadata_frame_test)

    def load_meta_data(self, sep="\t"):
        """
        """

        if isfile("{0}/{1}".format(self.path_data, self.metadata_tsv)):
            self.metadata_tsv = "{0}/{1}".format(
                self.path_data, self.metadata_tsv)

        if not self.metadata_tsv:
            return

        frame = pd.read_csv(self.metadata_tsv, sep=sep, index_col=0)

        ## FULL ##
        if self.sample_ids_full:
            diff = set(self.sample_ids_full).difference(frame.index)

            if diff:
                raise(Exception("Error! sample not present in metadata: {0}".format(
                    list(diff)[:5])))

            self.metadata_frame_full = frame.T[self.sample_ids_full].T

            self.metadata_mat_full = convert_metadata_frame_to_matrix(
                self.metadata_frame_full)

        ## CV ##
        if len(self.sample_ids_cv):
            diff = set(self.sample_ids_cv).difference(frame.index)

            if diff:
                raise(Exception("Error! sample not present in metadata: {0}".format(
                    list(diff)[:5])))

            self.metadata_frame_cv = frame.T[self.sample_ids_cv].T
            self.metadata_mat_cv = convert_metadata_frame_to_matrix(
                self.metadata_frame_cv)

        ## ALL ##
        diff = set(self.sample_ids).difference(frame.index)

        if diff:
            raise(Exception("Error! sample not present in metadata: {0}".format(
                list(diff)[:5])))

        self.metadata_frame = frame.T[self.sample_ids].T
        self.metadata_mat = convert_metadata_frame_to_matrix(
            self.metadata_frame)

    def subset_training_sets(self, change_cv=False):
        """ """
        if not self.subset_training_with_meta:
            print("Not subsetting training dataset.")
            return

        if self.metadata_frame is None:
            print("No metadata parsed. Not subsetting training sets")
            return

        samples_subset = set()
        samples_subset_cv = set()

        for key, values in self.subset_training_with_meta.items():
            if not isinstance(values, list):
                values = [values]

            for value in values:
                if key not in self.metadata_frame:
                    raise(Exception("Subbseting keys does'nt not exists in the metadata {0}".format(
                        key)))

                index = self.metadata_frame[self.metadata_frame[key] == value].index

                if self.metadata_frame_cv is not None:
                    index_cv = self.metadata_frame_cv[self.metadata_frame_cv[key] == value].index
                    samples_subset_cv.update(index_cv)

                samples_subset.update(index)

        new_index = translate_index(self.sample_ids, samples_subset)

        for key in self.matrix_train_array:
            self.matrix_train_array[key] = self.matrix_train_array[key][new_index]
        for key in self.matrix_ref_array:
            self.matrix_ref_array[key] = self.matrix_ref_array[key][new_index]
        for key in self.matrix_array:
            self.matrix_array[key] = self.matrix_array[key][new_index]

        self.survival = self.survival[new_index]

        self.metadata_frame = self.metadata_frame.T[list(samples_subset)].T
        self.metadata_mat = convert_metadata_frame_to_matrix(
            self.metadata_frame)

        self.sample_ids = list(samples_subset)

        if self.survival_cv is not None:
            new_index_cv = translate_index(self.sample_ids_cv,
                                           samples_subset_cv)
            for key in self.matrix_cv_array:
                self.matrix_cv_array[key] = self.matrix_cv_array[key][new_index_cv]

                if key in self.matrix_cv_unormalized_array:
                    self.matrix_cv_unormalized_array[key] = self.matrix_cv_unormalized_array[
                        key][new_index_cv]

            self.metadata_frame_cv = self.metadata_frame_cv.T[
                list(samples_subset_cv)].T
            self.metadata_mat_cv = convert_metadata_frame_to_matrix(
                self.metadata_frame_cv)

            self.sample_ids_cv = list(samples_subset_cv)
            self.survival_cv = self.survival_cv[new_index_cv]

    def load_new_test_dataset(self, tsv_dict,
                              path_survival_file=None,
                              survival_flag=None,
                              normalization=None,
                              metadata_file=None):
        """
        """
        if normalization is not None:
            normalization = defaultdict(bool, normalization)
        else:
            normalization = self.normalization.copy()

        self.test_tsv = tsv_dict.copy()

        for key in tsv_dict:
            if key not in self.training_tsv:
                self.test_tsv.pop(key)

        self.survival_test = None
        self.sample_ids_test = None

        self.metadata_frame_test = None
        self.metadata_mat_test = None

        self.survival_tsv_test = path_survival_file

        self.matrix_test_array = {}
        self.matrix_ref_array = {}
        self.feature_test_array = {}
        self.feature_ref_array = {}
        self.feature_ref_index = {}

        self.load_matrix_test(normalization)
        self.load_survival_test(survival_flag)
        self.load_meta_data_test(metadata_file=metadata_file)

    def _create_ref_matrix(self, key):
        """ """
        features_test = self.feature_test_array[key]

        features_train = self.feature_train_array[key]
        matrix_train = self.matrix_ref_array[key]

        test_dict = {feat: pos for pos, feat in enumerate(features_test)}
        train_dict = {feat: pos for pos, feat in enumerate(features_train)}

        index = [train_dict[feat] for feat in features_test]

        self.feature_ref_array[key] = self.feature_test_array[key]
        self.matrix_ref_array[key] = np.nan_to_num(matrix_train.T[index].T)

        self.feature_ref_index[key] = test_dict

    def load_array(self):
        """ """
        if self.verbose:
            print('loading data...')
        t = time()

        self.feature_array = {}
        self.matrix_array = {}

        data = list(self.data_type)[0]
        f_name = self.training_tsv[data]

        self.sample_ids, feature_ids, matrix = load_data_from_tsv(
            f_name=f_name,
            key=data,
            path_data=self.path_data)

        if self.verbose:
            print('{0} loaded of dim:{1}'.format(f_name, matrix.shape))
#         print('{0} loaded of dim:{1}'.format(f_name, matrix.shape))
        
        self.feature_array[data] = feature_ids
        self.matrix_array[data] = matrix

        for data in self.data_type[1:]:

            f_name = self.training_tsv[data]
            sample_ids, feature_ids, matrix = load_data_from_tsv(
                f_name=f_name,
                key=data,
                path_data=self.path_data)

            if self.sample_ids != sample_ids:
                print('#### Different patient ID for {0} matrix ####'.format(data))

                index1, index2, sample_ids = return_intersection_indexes(
                    self.sample_ids, sample_ids)

                self.sample_ids = sample_ids
                matrix = matrix[index2]

                for data2 in self.matrix_array:
                    self.matrix_array[data2] = self.matrix_array[data2][index1]

            self.feature_array[data] = feature_ids
            self.matrix_array[data] = matrix

            if self.verbose:
                print('{0} loaded of dim:{1}'.format(f_name, matrix.shape))

        self._discard_training_samples()

        if self.verbose:
            print('data loaded in {0} s'.format(time() - t))

    def _discard_training_samples(self):
        """
        """
        if self.normalization['DISCARD_TRAINING_SAMPLES']:
            sample_reducer = SampleReducer(1.0 - self.normalization['DISCARD_TRAINING_SAMPLES'])
            index = range(len(self.sample_ids))
            to_keep, to_remove = sample_reducer.sample_to_keep(self.matrix_array, index)

            self.sample_ids = np.asarray(self.sample_ids)[to_keep].tolist()

            for key in self.matrix_array:
                self.matrix_array[key] = self.matrix_array[key][to_keep]

            if self.verbose:
                print('{0} training samples discarded'.format(len(to_remove)))

    def reorder_matrix_array(self, new_sample_ids):
        """
        """
        assert(set(new_sample_ids) == set(self.sample_ids))
        index_dict = {sample: pos for pos, sample in enumerate(self.sample_ids)}
        index = [index_dict[sample] for sample in new_sample_ids]

        self.sample_ids = np.asarray(self.sample_ids)[index].tolist()

        for key in self.matrix_array:
            self.matrix_array[key] = self.matrix_array[key][index]

        self.survival = self.survival[index]

    def create_a_cv_split(self):
        """ """
        if not self.cross_validation_instance:
            return

        cv = self.cross_validation_instance

        if isinstance(self.cross_validation_instance, tuple):
            train, test = self.cross_validation_instance
        else:
            train, test = [(tn, tt)
                           for tn, tt in
                           cv.split(self.sample_ids)][self.test_fold]

        if self.normalization['PERC_SAMPLE_TO_KEEP']:
            sample_reducer = SampleReducer(self.normalization['PERC_SAMPLE_TO_KEEP'])
            to_keep, to_remove = sample_reducer.sample_to_keep(self.matrix_array, train)

            test = list(train[to_remove]) + list(test)
            train = train[to_keep]

        for key in self.matrix_array:
            self.matrix_cv_array[key] = self.matrix_array[key][test]
            self.matrix_array[key] = self.matrix_array[key][train]

        self.survival_cv = self.survival.copy()[test]
        self.survival = self.survival[train]

        if self.metadata_frame is not None:
            # cv
            self.metadata_frame_cv = self.metadata_frame.T[
                list(np.asarray(self.sample_ids)[test])].T
            self.metadata_mat_cv = self.metadata_mat.T[test].T
            self.metadata_mat_cv.index = range(len(test))
            # train
            self.metadata_frame = self.metadata_frame.T[
                list(np.asarray(self.sample_ids)[train])].T
            self.metadata_mat = self.metadata_mat.T[train].T
            self.metadata_mat.index = range(len(train))

        self.sample_ids_cv = np.asarray(self.sample_ids)[test].tolist()
        self.sample_ids = np.asarray(self.sample_ids)[train].tolist()

    def load_matrix_full(self):
        """
        """
        if self._full_loaded:
            return

        if not self.cross_validation_instance:
            self.matrix_full_array = self.matrix_train_array
            self.sample_ids_full = self.sample_ids
            self.survival_full = self.survival
            self.metadata_frame_full = self.metadata_frame
            self.metadata_mat_full = self.metadata_mat
            return

        if not self._cv_loaded:
            self.load_matrix_test_fold()

        for key in self.matrix_train_array:
            self.matrix_full_array[key] = vstack([self.matrix_train_array[key],
                                                  self.matrix_cv_array[key]])

        self.sample_ids_full = self.sample_ids[:] + self.sample_ids_cv[:]
        self.survival_full = vstack([self.survival, self.survival_cv])

        if self.metadata_frame is not None:
            self.metadata_frame_full = pd.concat([self.metadata_frame,
                                                  self.metadata_frame_cv])
            self.metadata_mat_full = pd.concat([self.metadata_mat,
                                                  self.metadata_mat_cv])
            self.metadata_mat_full.index = range(len(self.sample_ids_full))

        self._full_loaded = True

    def load_survival(self):
        """ """
        survival = load_survival_file(self.survival_tsv, path_data=self.path_data,
                                      survival_flag=self.survival_flag)
        matrix = []

        retained_samples = []
        sample_removed = 0

        for ids, sample in enumerate(self.sample_ids):
            if sample not in survival:
                sample_removed += 1
                continue

            retained_samples.append(ids)
            matrix.append(survival[sample])

        self.survival = np.asmatrix(matrix)

        if sample_removed:
            for key in self.matrix_array:
                self.matrix_array[key] = self.matrix_array[key][retained_samples]

            self.sample_ids = np.asarray(self.sample_ids)[retained_samples]

            if self.verbose:
                print('{0} samples without survival removed'.format(sample_removed))

    def load_survival_test(self, survival_flag=None):
        """ """
        if self.survival_tsv_test is None:
            self.survival_test = np.empty(
                shape=(len(self.sample_ids_test), 2))

            self.survival_test[:] = np.nan

            return

        if survival_flag is None:
            survival_flag = self.survival_flag

        survival = load_survival_file(self.survival_tsv_test,
                                      path_data=self.path_data,
                                      survival_flag=survival_flag)
        matrix = []

        retained_samples = []
        sample_removed = 0

        for ids, sample in enumerate(self.sample_ids_test):
            if sample not in survival:
                sample_removed += 1
                continue

            retained_samples.append(ids)
            matrix.append(survival[sample])

        self.survival_test = np.asmatrix(matrix)

        if sample_removed:
            for key in self.matrix_test_array:
                self.matrix_test_array[key] = self.matrix_test_array[key][retained_samples]

            self.sample_ids_test = np.asarray(self.sample_ids_test)[retained_samples]

            if self.verbose:
                print('{0} samples without survival removed'.format(sample_removed))

    def _define_train_features(self, key):
        """ """
        self.feature_train_array[key] = self.feature_array[key][:]

        if self.normalization['TRAIN_CORR_REDUCTION']:
            self.feature_train_array[key] = ['{0}_{1}'.format(key, sample)
                                             for sample in self.sample_ids]
        elif self.normalization['NB_FEATURES_TO_KEEP']:
            self.feature_train_array[key] = np.array(self.feature_train_array[key])[
                self.variance_reducer.index_to_keep].tolist()

        self.feature_ref_array[key] = self.feature_train_array[key]

        self.feature_train_index[key] = {key: id for id, key in enumerate(
            self.feature_train_array[key])}
        self.feature_ref_index[key] = self.feature_train_index[key]

    def _define_test_features(self, key, normalization=None):
        """ """
        if normalization is None:
            normalization = self.normalization

        if normalization['TRAIN_CORR_REDUCTION']:
            self.feature_test_array[key] = ['{0}_{1}'.format(key, sample)
                                             for sample in self.sample_ids]

        elif normalization['NB_FEATURES_TO_KEEP']:
            self.feature_test_array[key] = np.array(self.feature_test_array[key])[
                self.variance_reducer.index_to_keep].tolist()

    def _define_ref_features(self, key, normalization=None):
        """ """
        if normalization is None:
            normalization = self.normalization

        if normalization['TRAIN_CORR_REDUCTION']:
            self.feature_ref_array[key] = ['{0}_{1}'.format(key, sample)
                                           for sample in self.sample_ids]

            self.feature_ref_index[key] = {feat:pos for pos, feat in
                                           enumerate(self.feature_ref_array[key])}

        elif normalization['NB_FEATURES_TO_KEEP']:
            self.feature_ref_index[key] = {feat: pos for pos, feat in
                                           enumerate(self.feature_ref_array[key])}

    def normalize_training_array(self):
        """ """
        for key in self.matrix_array:
            matrix = self.matrix_array[key].copy()
#             print(matrix.shape)
            matrix = self._normalize(matrix, key)
#             print(matrix.shape)

            self.matrix_train_array[key] = matrix
            self.matrix_ref_array[key] = self.matrix_train_array[key]
            self._define_train_features(key)

        self._stack_multiomics(self.matrix_train_array, self.feature_train_array)
        self._stack_multiomics(self.matrix_ref_array, self.feature_ref_array)
        self._stack_index()

    def _stack_index(self):
        """
        """
        if not self.do_stack_multi_omic:
            return

        index = {'STACKED':{}}
        count = 0

        for key in self.feature_train_index:
            for feature in self.feature_train_index[key]:
                index['STACKED'][feature] = count + self.feature_train_index[key][feature]

            count += len(self.feature_train_index[key])

        self.feature_train_index = index
        self.feature_ref_index = self.feature_train_index

    def _normalize(self, matrix, key):
        """ """
        if self.verbose:
            print('normalizing for {0}...'.format(key))

        if self.normalization['NB_FEATURES_TO_KEEP']:
            self.variance_reducer.nb_features = self.normalization[
                'NB_FEATURES_TO_KEEP']
            matrix = self.variance_reducer.fit_transform(matrix)

        if self.normalization['CUSTOM']:
            custom_norm = self.normalization['CUSTOM']()
            assert(hasattr(custom_norm, 'fit') and hasattr(
                custom_norm, 'fit_transform'))
            matrix = custom_norm.fit_transform(matrix)

        if self.normalization['TRAIN_MIN_MAX']:
            matrix = MinMaxScaler().fit_transform(matrix.T).T

        if self.normalization['TRAIN_MAD_SCALE']:
            matrix = self.mad_scaler.fit_transform(matrix.T).T

        if self.normalization['TRAIN_ROBUST_SCALE'] or\
           self.normalization['TRAIN_ROBUST_SCALE_TWO_WAY']:
            matrix = self.robust_scaler.fit_transform(matrix)

        if self.normalization['TRAIN_NORM_SCALE']:
            matrix = self.normalizer.fit_transform(matrix)

        if self.normalization['TRAIN_QUANTILE_TRANSFORM']:
            matrix = quantile_transform(matrix, **QUANTILE_OPTION)

        if self.normalization['TRAIN_RANK_NORM']:
            matrix = RankNorm().fit_transform(
                matrix)

        if self.normalization['TRAIN_CORR_REDUCTION']:
            args = self.normalization['TRAIN_CORR_REDUCTION']
            if args == True:
                args = {}

            if self.verbose:
                print('dim reduction for {0}...'.format(key))

            reducer = CorrelationReducer(**args)
            matrix = reducer.fit_transform(
                matrix)

            if self.normalization['TRAIN_CORR_RANK_NORM']:
                matrix = RankNorm().fit_transform(
                    matrix)

            if self.normalization['TRAIN_CORR_QUANTILE_NORM']:
                matrix = quantile_transform(matrix, **QUANTILE_OPTION)

            if self.normalization['TRAIN_CORR_NORM_SCALE']:
                matrix = self.normalizer.fit_transform(matrix)

        return np.nan_to_num(matrix)

    def transform_matrices(self, matrix_ref, matrix, key, normalization=None):
        """ """
        if normalization is None:
            normalization = self.normalization

        if self.verbose:
            print('Scaling/Normalising dataset...')

        if normalization['LOG_REF_MATRIX']:
            matrix_ref = np.log2(1.0 + matrix_ref)

        if normalization['LOG_TEST_MATRIX']:
            matrix = np.log2(1.0 +  matrix)

        if self.normalization['CUSTOM']:
            custom_norm = self.normalization['CUSTOM']()
            assert(hasattr(custom_norm, 'fit') and hasattr(
                custom_norm, 'fit_transform'))
            matrix_ref = custom_norm.fit_transform(matrix_ref)
            matrix = custom_norm.transform(matrix)

        if normalization['NB_FEATURES_TO_KEEP']:
            self.variance_reducer.nb_features = normalization[
                'NB_FEATURES_TO_KEEP']
            matrix_ref = self.variance_reducer.fit_transform(matrix_ref)
            matrix = self.variance_reducer.transform(matrix)

        if normalization['TRAIN_MIN_MAX']:
            matrix_ref = self.min_max_scaler.fit_transform(matrix_ref.T).T
            matrix = self.min_max_scaler.fit_transform(matrix.T).T

        if normalization['TRAIN_MAD_SCALE']:
            matrix_ref = self.mad_scaler.fit_transform(matrix_ref.T).T
            matrix = self.mad_scaler.fit_transform(matrix.T).T

        if normalization['TRAIN_ROBUST_SCALE']:
            matrix_ref = self.robust_scaler.fit_transform(matrix_ref)
            matrix = self.robust_scaler.transform(matrix)

        if normalization['TRAIN_ROBUST_SCALE_TWO_WAY']:
            matrix_ref = self.robust_scaler.fit_transform(matrix_ref)
            matrix = self.robust_scaler.transform(matrix)

        if normalization['TRAIN_NORM_SCALE']:
            matrix_ref = self.normalizer.fit_transform(matrix_ref)
            matrix = self.normalizer.transform(matrix)

        if self.normalization['TRAIN_QUANTILE_TRANSFORM']:
            matrix_ref = quantile_transform(matrix_ref, **QUANTILE_OPTION)
            matrix = quantile_transform(matrix, **QUANTILE_OPTION)

        if normalization['TRAIN_RANK_NORM']:
            matrix_ref = RankNorm().fit_transform(matrix_ref)
            matrix = RankNorm().fit_transform(matrix)

        if normalization['TRAIN_CORR_REDUCTION']:
            args = normalization['TRAIN_CORR_REDUCTION']

            if args == True:
                args = {}

            reducer = CorrelationReducer(**args)
            matrix_ref = reducer.fit_transform(matrix_ref)
            matrix = reducer.transform(matrix)

            if normalization['TRAIN_CORR_RANK_NORM']:
                matrix_ref = RankNorm().fit_transform(matrix_ref)
                matrix = RankNorm().fit_transform(matrix)

            if self.normalization['TRAIN_CORR_QUANTILE_TRANSFORM']:
                matrix_ref = quantile_transform(matrix_ref, **QUANTILE_OPTION)
                matrix = quantile_transform(matrix, **QUANTILE_OPTION)

            if self.normalization['TRAIN_CORR_NORM_SCALE']:
                matrix_ref = self.normalizer.fit_transform(matrix_ref)
                matrix = self.normalizer.fit_transform(matrix)

        return np.nan_to_num(matrix_ref), np.nan_to_num(matrix)

    def save_ref_matrix(self, path_folder, project_name):
        """
        """
        for key in self.matrix_ref_array:
            save_matrix(
                matrix=self.matrix_ref_array[key],
                feature_array=self.feature_ref_array[key],
                sample_array=self.sample_ids,
                path_folder=path_folder,
                project_name=project_name,
                key=key
            )
