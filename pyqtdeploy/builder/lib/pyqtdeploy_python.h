#include <pyconfig.h>
#if defined(__GNUG__) && defined(HAVE_STD_ATOMIC)
#undef HAVE_STD_ATOMIC
#endif

#include <Python.h>
