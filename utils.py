def format_money(raw_value):
    """
    Format money based on raw values.
    1 Crore = 10000000
    1 Lakh = 100000
    Examples:
    20000000 -> ₹2.00 Cr
    5000000 -> ₹50.00 Lakh
    """
    if raw_value is None:
        return "₹0.00 Cr"
        
    try:
        val = float(raw_value)
    except (ValueError, TypeError):
        return "₹0.00 Cr"

    if val >= 10000000:
        return f"₹{val / 10000000:.2f} Cr"
    elif val >= 100000:
        return f"₹{val / 100000:.2f} Lakh"
    else:
        return f"₹{val:,.2f}"
