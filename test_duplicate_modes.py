import os

def test_no_duplicate_modes():
    """
    Tests that the duplicated mode files do not exist in core/mcp/modes/.
    """
    base_path = 'core/mcp/modes'
    
    auto_research_path = os.path.join(base_path, 'auto_research_mode.json')
    code_runner_path = os.path.join(base_path, 'code_runner_mode.json')
    
    assert not os.path.exists(auto_research_path), \
        f"Duplicate mode file found: {auto_research_path}"
        
    assert not os.path.exists(code_runner_path), \
        f"Duplicate mode file found: {code_runner_path}"

if __name__ == "__main__":
    test_no_duplicate_modes()
    print("Test passed!")
