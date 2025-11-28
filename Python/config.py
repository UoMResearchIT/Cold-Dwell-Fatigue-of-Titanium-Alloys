import os
from types import SimpleNamespace
from dotenv import load_dotenv, find_dotenv


class Config:
    def __init__(self, env_file=find_dotenv()):
        load_dotenv(env_file)

        self.dream3d_version = os.getenv("DREAM3D_VERSION")
        self.dream3d_pipeline_runner = os.getenv("DREAM3D_PIPELINE_RUNNER")

        self._dream3d_pipeline_template = os.getenv("DREAM3D_PIPELINE_TEMPLATE")

        self.error_handling = SimpleNamespace(
            timeout_seconds=int(os.getenv("DREAM3D_TIMEOUT_SECONDS", "120"))
        )

        for a, v in self.__dict__.items():
            if isinstance(v, SimpleNamespace):
                for b, w in v.__dict__.items():
                    assert (
                        w is not None
                    ), f"{a.upper()}_{b.upper()} not set in environment"
            else:
                assert v is not None, f"{a.upper()} not set in environment"

    def dream3d_pipeline_template(self, ext: str) -> str:
        return self._dream3d_pipeline_template.format(EXT=ext.upper(), ext=ext.lower())
