import os
from types import SimpleNamespace
from dotenv import load_dotenv


class Config():
    def __init__(self, env_file='.env'):
        load_dotenv(env_file)

        self.dream3d_version = os.getenv('DREAM3D_VERSION')
        self.dream3d_pipeline_runner_location = os.getenv('DREAM3D_PIPELINE_RUNNER_LOCATION')
        self.dream3d_pipeline_template_location = SimpleNamespace(
            ctf=os.getenv('DREAM3D_PIPELINE_TEMPLATE_LOCATION_CTF'),
            ang=os.getenv('DREAM3D_PIPELINE_TEMPLATE_LOCATION_ANG')
        )
        self.error_handling = SimpleNamespace(
            timeout_seconds=int(os.getenv('DREAM3D_TIMEOUT_SECONDS', '120'))
        )

        for a, v in self.__dict__.items():
            if isinstance(v, SimpleNamespace):
                for b, w in v.__dict__.items():
                    assert w is not None, f"{a.upper()}_{b.upper()} not set in environment"
            else:
                assert v is not None, f"{a.upper()} not set in environment"

        for ext, template in self.dream3d_pipeline_template_location.__dict__.items():
            assert os.path.isfile(template), f"{ext.upper()} template: {template} not found"

        assert os.path.isfile(self.dream3d_pipeline_runner_location), f"DREAM3D Pipeline Runner not found at: {self.dream3d_pipeline_runner_location}"
