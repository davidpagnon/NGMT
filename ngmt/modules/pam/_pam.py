import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ngmt.config import cfg_colors
from ngmt.utils import preprocessing


class PhysicalActivityMonitoring:
    """
    Monitors physical activity levels based on accelerometer data.

    Description:
        The algorithm determines the intensity level of physical activities based on accelerometer
        signals using the following steps:

        - Load Data: Includes a time index and accelerometer data (N, 3) for x, y, and z axes. The
          sampling frequency (sampling_freq_Hz) is in Hz, with a default value of 100. Thresholds
          (thresholds_mg) are provided as a dictionary containing threshold values for physical
          activity detection in mg unit. The epoch duration (epoch_duration_sec) is defined in
          seconds, with a default of 5 seconds. The last input is plot_results, which, if set to
          True, generates a plot showing the average Euclidean Norm Minus One (ENMO) per hour for
          each date. The default is True.

        - Preprocess Signal: Calculate the sample-level Euclidean norm (EN) of the acceleration
          signal. Apply a fourth-order Butterworth low-pass filter with a cut-off frequency of 20Hz
          to remove noise. Calculate the Euclidean Norm Minus One (ENMO) index and truncate negative
          values to zero. Convert the indices by multiplying them by 1000 to convert units from g to
          mg.

        - Classify Intensity: Classify the intensity of physical activities based on the calculated
          ENMO values using 5-second epochs. Thresholds for categorization are as follows: sedentary
          activity < 45 mg, light activity 45–100 mg, moderate activity 100–400 mg, vigorous activity
          > 400 mg.

        - Classify Activities: Classify different levels of activities and calculate the time spent
          on each activity level for each day. If `plot_results` is True, the function generates a
          plot showing the averaged ENMO values for each day.

    Attributes:
        physical_activities_ (pd.DataFrame): DataFrame containing physical activity information for each day.

    Methods:
        detect(data, sampling_freq_Hz, thresholds_mg, epoch_duration_sec, plot_results):
            Detects gait sequences on the accelerometer signal.

        __init__():
            Initializes the physical activity instance.

        Examples:
            Determines physical activity levels in the sensor signal.

            >>> pam = PhysicalActivityMonitoring()
            >>> pam.detect(
                    data=acceleration_data,
                    sampling_freq_Hz=100,
                    thresholds_mg={
                        "sedentary_threshold": 45,
                        "light_threshold": 100,
                        "moderate_threshold": 400,
                    },
                    epoch_duration_sec=5,
                    plot_results=True)
            >>> physical_activities = pam.physical_activities_
            >>> print(physical_activities)
                           sedentary_mean_mg  sedentary_time_min  light_mean_mg  light_time_min  moderate_mean_mg  moderate_time_min  vigorous_mean_mg  vigorous_time_min
            3/19/2018               23.48               733.08          60.78              72             146.2              21.58             730.34                0.58
            3/20/2018               27.16               753.83          57.06           102.25            137.26               7.92             737.9                 0.42

        References:
            [1] Doherty, Aiden, et al. (2017). Large scale population assessment of physical
                activity using wrist-worn accelerometers: the UK biobank study. PloS one 12.2.
                https://doi.org/10.1371/journal.pone.0169649

            [2] Van Hees, Vincent T., et al. (2013). Separating movement and gravity components
                in an acceleration signal and implications for the assessment of human daily physical
                activity. PloS one 8.4. https://doi.org/10.1371/journal.pone.0061691
    """

    def __init__(self):
        """
        Initializes the physical activity instance.
        """
        self.physical_activities_ = None

    def detect(
        self,
        data: pd.DataFrame,
        sampling_freq_Hz: float,
        thresholds_mg: dict = {
            "sedentary_threshold": 45,
            "light_threshold": 100,
            "moderate_threshold": 400,
        },
        epoch_duration_sec: int = 5,
        plot_results: bool = True,
    ) -> pd.DataFrame:
        """
        Detects and classifies physical activity levels.

        Args:
            data (pd.DataFrame): Input data with time index and accelerometer data (N, 3) for x, y, and z axes.
            sampling_freq_Hz (float): Sampling frequency of the accelerometer data (in Hertz).
            thresholds_mg (dict): Dictionary containing threshold values for physical activity detection.
            epoch_duration_sec (int): Duration of each epoch in seconds.
            plot_results (bool): If True, generates a plot showing the average Euclidean Norm Minus One (ENMO). Default is True.

        Returns:
            pd.DataFrame: Contains date, sedentary_mean_mg, sedentary_time_min, light_mean_mg, light_time_min,
                          moderate_mean_mg, moderate_time_min, vigorous_mean_mg, vigorous_time_min
        """
        # Error handling for invalid input data
        if not isinstance(sampling_freq_Hz, (int, float)) or sampling_freq_Hz <= 0:
            raise ValueError("Sampling frequency must be a positive float.")

        if not isinstance(thresholds_mg, dict):
            raise ValueError("Thresholds must be a dictionary.")

        if not isinstance(epoch_duration_sec, int) or epoch_duration_sec <= 0:
            raise ValueError("Epoch duration must be a positive integer.")

        if not isinstance(plot_results, bool):
            raise ValueError("Plot results must be a boolean (True or False).")

        # Calculate Euclidean Norm (EN)
        data["en"] = np.linalg.norm(data[["Acc_x", "Acc_y", "Acc_z"]], axis=1)

        # Apply 4th order low-pass Butterworth filter with the cutoff frequency of 20Hz
        data["en"] = preprocessing.lowpass_filter(
            data["en"].values,
            method="butter",
            order=4,
            cutoff_freq_hz=20,
            sampling_rate_hz=sampling_freq_Hz,
        )

        # Calculate Euclidean Norm Minus One (ENMO) value
        data["enmo"] = data["en"] - 1

        # Set negative values of ENMO to zero
        data["truncated_enmo"] = np.maximum(data["enmo"], 0)

        # Convert ENMO from g to milli-g
        data["enmo"] = data["truncated_enmo"] * 1000

        # Create a final DataFrame with time index and processed ENMO values
        processed_data = pd.DataFrame(
            data=data["enmo"], index=data.index, columns=["enmo"]
        )

        # Classify activities based on thresholds using activity_classification
        classified_processed_data = preprocessing.classify_physical_activity(
            processed_data,
            sedentary_threshold=thresholds_mg.get("sedentary_threshold", 45),
            light_threshold=thresholds_mg.get("light_threshold", 100),
            moderate_threshold=thresholds_mg.get("moderate_threshold", 400),
            epoch_duration=epoch_duration_sec,
        )

        # Extract date from the datetime index
        classified_processed_data["date"] = classified_processed_data["time"].dt.date

        # Calculate time spent in each activity level for each epoch
        classified_processed_data["sedentary_time_min"] = (
            classified_processed_data["sedentary"] * epoch_duration_sec
        ) / 60
        classified_processed_data["light_time_min"] = (
            classified_processed_data["light"] * epoch_duration_sec
        ) / 60
        classified_processed_data["moderate_time_min"] = (
            classified_processed_data["moderate"] * epoch_duration_sec
        ) / 60
        classified_processed_data["vigorous_time_min"] = (
            classified_processed_data["vigorous"] * epoch_duration_sec
        ) / 60

        # Group by date and calculate mean and total time spent in each activity level
        physical_activities_ = (
            classified_processed_data.groupby("date")
            .agg(
                sedentary_mean_enmo=(
                    "enmo",
                    lambda x: np.mean(x[classified_processed_data["sedentary"] == 1]),
                ),
                sedentary_time_min=("sedentary_time_min", "sum"),
                light_mean_enmo=(
                    "enmo",
                    lambda x: np.mean(x[classified_processed_data["light"] == 1]),
                ),
                light_time_min=("light_time_min", "sum"),
                moderate_mean_enmo=(
                    "enmo",
                    lambda x: np.mean(x[classified_processed_data["moderate"] == 1]),
                ),
                moderate_time_min=("moderate_time_min", "sum"),
                vigorous_mean_enmo=(
                    "enmo",
                    lambda x: np.mean(x[classified_processed_data["vigorous"] == 1]),
                ),
                vigorous_time_min=("vigorous_time_min", "sum"),
            )
            .reset_index()
        )

        # Return gait_sequences_ as an output
        self.physical_activities_ = physical_activities_

        # Plot results if set to true
        if plot_results:
            # Group by date and hour to calculate the average ENMO for each hour
            hourly_average_data = processed_data.groupby(
                [processed_data.index.date, processed_data.index.hour]
            )["enmo"].mean()

            # Reshape the data to have dates as rows, hours as columns, and average ENMO as values
            hourly_average_data = hourly_average_data.unstack()

            # Plotting
            fig, ax = plt.subplots(figsize=(14, 8))

            # Choose the 'turbo' colormap for coloring each day
            colormap = plt.cm.get_cmap("turbo", len(hourly_average_data.index))

            # Plot thresholds
            ax.axhline(
                y=thresholds_mg.get("sedentary_threshold", 45),
                color="y",
                linestyle="--",
                label="Sedentary threshold",
            )
            ax.axhline(
                y=thresholds_mg.get("light_threshold", 100),
                color="g",
                linestyle="--",
                label="Light physical activity threshold",
            )
            ax.axhline(
                y=thresholds_mg.get("moderate_threshold", 400),
                color="r",
                linestyle="--",
                label="Moderate physical activity threshold",
            )

            # Plot each day data with a different color
            for i, date in enumerate(hourly_average_data.index):
                color = colormap(i)
                ax.plot(hourly_average_data.loc[date], label=str(date), color=color)

            # Customize plot appearance
            plt.xticks(range(24), [str(i).zfill(2) for i in range(24)])
            plt.xlabel("Time (h)", fontsize=16)
            plt.ylabel("ENMO (mg)", fontsize=16)
            plt.title(
                "Hourly averaged ENMO for each day along with activity level thresholds"
            )
            plt.legend(loc="upper left", fontsize=16)
            plt.grid(visible=None, which="both", axis="both")
            plt.xticks(fontsize=16)
            plt.yticks(fontsize=16)
            plt.tight_layout()
            plt.show()

        return self
