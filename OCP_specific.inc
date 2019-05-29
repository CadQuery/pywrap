#include <Standard_Handle.hxx>

namespace py = pybind11;

PYBIND11_DECLARE_HOLDER_TYPE(T, opencascade::handle<T>, true);

template<typename T> struct Deleter { void operator() (T *o) const { delete o; } };

using opencascade::handle;