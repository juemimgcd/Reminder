from pathlib import Path
import unittest

import yaml


COMPOSE_FILE = Path(__file__).resolve().parents[1] / "docker-compose.yml"


class DockerComposeContractTest(unittest.TestCase):
    def setUp(self):
        self.compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
        self.services = self.compose["services"]

    def test_app_build_uses_docker_directory_dockerfile(self):
        self.assertEqual(self.compose["x-app-base"]["build"]["dockerfile"], "docker/Dockerfile")

    def test_vector_stack_is_opt_in_profile(self):
        for service_name in ("etcd", "minio", "milvus"):
            with self.subTest(service=service_name):
                self.assertEqual(self.services[service_name].get("profiles"), ["vector"])

    def test_app_stack_does_not_wait_for_milvus_by_default(self):
        app_base = self.compose["x-app-base"]
        environment = app_base["environment"]

        self.assertNotIn("milvus", environment["WAIT_FOR_HOSTS"])
        self.assertNotIn("milvus", environment["WAIT_FOR_URLS"])
        self.assertEqual(environment["MILVUS_URI"], "${MILVUS_URI:-http://milvus:19530}")

    def test_migrate_does_not_depend_on_profiled_milvus_service(self):
        migrate_dependencies = self.services["migrate"]["depends_on"]

        self.assertNotIn("milvus", migrate_dependencies)


if __name__ == "__main__":
    unittest.main()
