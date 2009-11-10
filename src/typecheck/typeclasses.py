# Name: 		typecheck
# Version: 		0.3.5
# Summary: 		A runtime type-checking module for Python
# Home-page: 	http://oakwinter.com/code/typecheck/
# Author: 		Collin Winter
# Author-email: collinw@gmail.com
# License: 		MIT License
# Description: 	A runtime type-checking module for Python supporting both parameter-type checking and 
# 	return-type checking for functions, methods and generators. The main workhorses of this module, 
# 	the functions `accepts` and `returns`, are used as function/method decorators. A `yields` decorator 
#	provides a mechanism to typecheck the values yielded by generators. Four utility classes, 
# 	IsAllOf(), IsOneOf(), IsNoneOf() and IsOnlyOneOf() are provided to assist in building more complex 
#	signatures by creating boolean expressions based on classes and/or types. A number of other utility 
#	classes exist to aid in type signature creation; for a full list, see the README.txt file or the 
#	project's website. The module also includes support for type variables, a concept borrowed from 
#	languages such as Haskell.

from typecheck import Typeclass

### Number
####################################################

_numbers = [int, float, complex, long, bool]
try:
    from decimal import Decimal
    _numbers.append(Decimal)
    del Decimal
except ImportError:
    pass
    
Number = Typeclass(*_numbers)
del _numbers
    
### String -- subinstance of ImSequence
####################################################

String = Typeclass(str, unicode)
    
### ImSequence -- immutable sequences
####################################################

ImSequence = Typeclass(tuple, xrange, String)

### MSequence -- mutable sequences
####################################################

MSequence = Typeclass(list)

### Mapping
####################################################

Mapping = Typeclass(dict)
