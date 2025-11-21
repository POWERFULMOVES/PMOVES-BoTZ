import yaml

def test_no_redundant_cipher_compose_definition():
    """
    Tests that the cipher-memory service is not defined in the generic
    features/cipher/docker-compose.yml, to avoid redundancy with the main
    pro-pack compose file.
    """
    with open('features/cipher/docker-compose.yml', 'r') as f:
        compose_data = yaml.safe_load(f) or {}

    assert 'cipher-memory' not in compose_data.get('services', {}), \
        "'cipher-memory' service should not be defined in features/cipher/docker-compose.yml"

if __name__ == "__main__":
    test_no_redundant_cipher_compose_definition()
    print("Test passed!")
