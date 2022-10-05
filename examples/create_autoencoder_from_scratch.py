"""
Create a new autoencoder model from scratch using user defined .tsv input files
"""

from simdeep.extract_data import LoadData
from simdeep.simdeep_analysis import SimDeep

from simdeep.config import PATH_DATA
from simdeep.config import PATH_TO_SAVE_MODEL


def main():
    """ """

    # Defining the path for the data
    # (we will the default path defined in config.py) but can be overloaded
    path_data = PATH_DATA
    print('path to access the .tsv files: '+ path_data)

    # Defining the path to save the autoencoder
    path_to_save_model = PATH_TO_SAVE_MODEL
    print('path where the models will be saved:' + path_to_save_model)

    # the dataset to be used
    # Here we will combine only two omics to create the autoencoder:
    # RNA and MIR.
    # We will use the dummy dataset available in the example folder
    #These files should be inside the dataset_path folder
    tsv_files = {
        'RNA': 'rna_dummy.tsv',
        'MIR': 'mir_dummy.tsv'
    }

    # survival file to be used
    survival_file = 'survival_dummy.tsv'

    # Metadata file (optional)
    metadata_file = "metadata_dummy.tsv"

    # class to load and prepare the data
    dataset = LoadData(path_data=path_data,
                       training_tsv=tsv_files,
                       survival_tsv=survival_file,
                       metadata_tsv=metadata_file # Optional
                       )

    simDeep = SimDeep(dataset=dataset,
                      path_to_save_model=path_to_save_model,
                      seed=2020
    )
    # dataset must be loaded
    simDeep.load_training_dataset()
    # model construction
    simDeep.fit()

    # predict on full dataset
    simDeep.predict_labels_on_full_dataset()
    # Finally, saving the model
    simDeep.save_encoders('encoder_example.h5')


if __name__ == "__main__":
    main()
