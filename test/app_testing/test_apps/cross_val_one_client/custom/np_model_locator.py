import os
from typing import List

import numpy as np

from constants import NPConstants
from nvflare.apis.dxo import DXO, DataKind
from nvflare.apis.fl_constant import FLContextKey
from nvflare.apis.fl_context import FLContext
from nvflare.app_common.abstract.model_locator import (
    ModelLocator,
)


class NPModelLocator(ModelLocator):
    SERVER_MODEL_NAME = "server"

    def __init__(self, model_dir="models", model_name="server.npy"):
        super().__init__()

        self.model_dir = model_dir
        self.model_file_name = model_name

    def get_model_names(self, fl_ctx: FLContext) -> List[str]:
        """Returns the list of model names that should be included from server in cross site validation.add()

        Args:
            fl_ctx (FLContext): FL Context object.

        Returns:
            List[str]: List of model names.
        """
        return [NPModelLocator.SERVER_MODEL_NAME]

    def locate_model(self, model_name, fl_ctx: FLContext) -> DXO:
        dxo = None
        engine = fl_ctx.get_engine()

        if model_name == NPModelLocator.SERVER_MODEL_NAME:
            run_number = fl_ctx.get_prop(FLContextKey.CURRENT_RUN)
            run_dir = engine.get_workspace().get_run_dir(run_number)
            model_path = os.path.join(run_dir, self.model_dir)

            model_load_path = os.path.join(model_path, self.model_file_name)
            np_data = None
            try:
                np_data = np.load(model_load_path, allow_pickle=True)
                self.log_info(fl_ctx, f"Loaded {model_name} model from {model_load_path}.")
            except Exception as e:
                self.log_error(fl_ctx, f"Unable to load NP Model: {e}.")

            if np_data is not None:
                weights = {NPConstants.NUMPY_KEY: np_data}
                dxo = DXO(data_kind=DataKind.WEIGHTS, data=weights, meta={})

        return dxo
