import re

def test_no_host_network_mode_in_docs():
    """
    Tests that the 'network_mode: host' is not present for the cipher-memory
    service in the documentation, which would be incorrect.
    """
    with open('docs/CIPHER_MEMORY_INTEGRATION.md', 'r') as f:
        content = f.read()

    # Find the cipher-memory service definition in the docker deployment section
    docker_deployment_section = re.search(r'## Docker Deployment\n\n(.*?)## Testing', content, re.DOTALL)
    assert docker_deployment_section is not None, "Docker Deployment section not found in docs/CIPHER_MEMORY_INTEGRATION.md"

    service_config = docker_deployment_section.group(1)
    
    # Check for 'network_mode: host' within the cipher-memory service block
    cipher_memory_service_block = re.search(r'cipher-memory:(.*?)(\n\S|$)', service_config, re.DOTALL)
    assert cipher_memory_service_block is not None, "cipher-memory service not found in Docker Deployment section"

    assert 'network_mode: host' not in cipher_memory_service_block.group(1), \
        "'network_mode: host' found in docs/CIPHER_MEMORY_INTEGRATION.md for cipher-memory service"

if __name__ == "__main__":
    test_no_host_network_mode_in_docs()
    print("Test passed!")
