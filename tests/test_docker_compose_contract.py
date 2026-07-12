from pathlib import Path
import unittest

import yaml


COMPOSE_FILE = Path(__file__).resolve().parents[1] / "docker-compose.yml"
NGINX_FILE = Path(__file__).resolve().parents[1] / "nginx" / "reminder.conf"
PRODUCTION_ENV_TEMPLATE = Path(__file__).resolve().parents[1] / "deploy" / "env" / "backend.production.example"
DOCKERIGNORE_FILE = Path(__file__).resolve().parents[1] / ".dockerignore"


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

    def test_neo4j_uses_an_existing_compatible_image(self):
        image = self.services["neo4j"]["image"]

        self.assertNotEqual(image, "neo4j:5.28")
        self.assertEqual(image, "neo4j:latest")

    def test_nginx_uses_the_production_hostname_and_private_upstream(self):
        nginx = NGINX_FILE.read_text(encoding="utf-8")

        self.assertIn("server_name www.mneme.com.cn;", nginx)
        self.assertIn("server 127.0.0.1:8000;", nginx)

    def test_production_template_uses_internal_neo4j_service(self):
        text = PRODUCTION_ENV_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("NEO4J_URI=bolt://neo4j:7687", text)
        self.assertNotIn("8.147.57.104", text)

    def test_document_hash_backfill_is_included_in_the_image_build_context(self):
        patterns = DOCKERIGNORE_FILE.read_text(encoding="utf-8").splitlines()

        self.assertIn("!scripts/", patterns)
        self.assertIn("scripts/*", patterns)
        self.assertIn("!scripts/backfill_document_hashes.py", patterns)


if __name__ == "__main__":
    unittest.main()
