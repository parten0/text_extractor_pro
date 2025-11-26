def validate_invoice(data):
    assert "metadata" in data
    assert "tables" in data
