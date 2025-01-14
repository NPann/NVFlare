import logging
import time

import numpy as np

from constants import NPConstants
from nvflare.apis.dxo import from_shareable, DataKind, DXO
from nvflare.apis.executor import Executor
from nvflare.apis.fl_constant import ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from nvflare.app_common.app_constant import AppConstants


class NPValidator(Executor):
    def __init__(
        self,
        epsilon=1,
        sleep_time=0,
        validate_task_name=AppConstants.TASK_VALIDATION,
    ):
        super().__init__()

        self.logger = logging.getLogger("NPValidator")
        self._random_epsilon = epsilon
        self._sleep_time = sleep_time
        self._validate_task_name = validate_task_name

    def execute(
        self,
        task_name: str,
        shareable: Shareable,
        fl_ctx: FLContext,
        abort_signal: Signal,
    ) -> Shareable:
        # Any kind of tasks waiting should check abort_signal regularly
        count, interval = 0, 0.5
        while count < self._sleep_time:
            if abort_signal.triggered:
                return self._abort_execution()
            time.sleep(interval)
            count += interval

        if task_name == self._validate_task_name:

            try:
                model_dxo = from_shareable(shareable)
            except Exception as e:
                self.log_error(f"Unable to extract model dxo from shareable. Exception: {(e.__str__())}")
                shareable.set_return_code(ReturnCode.EXECUTION_EXCEPTION)
                return shareable

            # Get model from shareable
            if model_dxo.data and model_dxo.data_kind == DataKind.WEIGHTS:
                model = model_dxo.data
            else:
                self.log_error(fl_ctx, f"Model Dex doesn't have data or is not of type DataKind.WEIGHTS. Unable  "
                                       "to validate.")
                shareable.set_return_code(ReturnCode.EXECUTION_EXCEPTION)
                return shareable

            model_name = shareable.get_header(AppConstants.MODEL_OWNER, "?")

            self.log_info(fl_ctx, f"Model: \n{model}")
            self.log_info(fl_ctx, f"Task name: {task_name}")
            self.log_info(fl_ctx, f"Client identity: {fl_ctx.get_identity_name()}")
            self.log_info(fl_ctx, f"Validating model from {model_name}.")

            # Check abort signal
            if abort_signal.triggered:
                return self._abort_execution()

            # Check if key exists in model
            if NPConstants.NUMPY_KEY not in model:
                self.log_error(fl_ctx, "numpy_key not in model. Unable to validate.")
                shareable.set_return_code(ReturnCode.EXECUTION_EXCEPTION)
                return shareable

            random_epsilon = np.random.random()
            self.log_info(
                fl_ctx, f"Adding random epsilon {random_epsilon} in validation."
            )

            # Do some dummy validation here
            val_results = {}
            np_data = model[NPConstants.NUMPY_KEY]
            np_data = np.sum(np_data / np.max(np_data))
            val_results["accuracy"] = np_data + random_epsilon

            # Check abort signal
            if abort_signal.triggered:
                return self._abort_execution()

            self.log_info(fl_ctx, f"Validation result: {val_results}")

            metric_dxo = DXO(data_kind=DataKind.METRICS, data=val_results)

            return metric_dxo.to_shareable()

        else:
            shareable = Shareable()
            shareable.set_return_code(ReturnCode.EXECUTION_EXCEPTION)
            return shareable

    def _abort_execution(self) -> Shareable:
        """Abort execution. This is used if abort_signal is triggered. Users should
        make sure they abort any running processes here.

        Returns:
            Shareable: Shareable with return_code.
        """
        shareable = Shareable()
        shareable.set_return_code(ReturnCode.EXECUTION_EXCEPTION)
        return shareable
