#==========================================================================================\\\
#============================ tools/patch_dynamics_nan.py ============================\\\
#==========================================================================================\\\
from pathlib import Path

p = Path('src/core/dynamics.py')
s = p.read_text(encoding='utf-8')

needle_if = 'if not np.all(np.isfinite(svals_reg)) or svals_reg[-1] <= 0.0:'
idx_if = s.find(needle_if)
assert idx_if != -1, 'if-guard not found'

# Find the start of the raise line after the if
idx_raise = s.find('raise NumericalInstabilityError', idx_if)
assert idx_raise != -1, 'raise not found after if'

# Find the closing parenthesis of the raise block
idx_close = s.find(')\n', idx_raise)
assert idx_close != -1, 'closing paren not found'
idx_close += 2  # include the newline after )

replacement = needle_if + "\n        return nan_vec\n"
patched = s[:idx_if] + replacement + s[idx_close:]

p.write_text(patched, encoding='utf-8')
print('patched dynamics.py raise->nan_vec')
