# `docker buildx bake` builds the app image on top of the local mise image.

target "mise" {
  context = "docker/mise"
}

# Filled with tags and labels by docker/metadata-action in CI.
target "docker-metadata-action" {}

target "prod" {
  inherits   = ["docker-metadata-action"]
  context    = "."
  dockerfile = "docker/Dockerfile"
  target     = "prod"
  contexts = {
    "localhost/mise:2026.9.0" = "target:mise"
  }
}

group "default" {
  targets = ["prod"]
}
