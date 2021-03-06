import unittest

import numpy

import cupy
from cupy.cuda import compiler
from cupy import testing


def _compile_func(kernel_name, code):
    mod = compiler.compile_with_cache(code)
    return mod.get_function(kernel_name)


@testing.gpu
class TestFunction(unittest.TestCase):

    def test_python_scalar(self):
        code = '''
extern "C" __global__ void test_kernel(const double* a, double b, double* x) {
  int i = threadIdx.x;
  x[i] = a[i] + b;
}
'''

        a_cpu = numpy.arange(24, dtype=numpy.float64).reshape((4, 6))
        a = cupy.array(a_cpu)
        b = float(2)
        x = cupy.empty_like(a)

        func = _compile_func('test_kernel', code)

        func.linear_launch(a.size, (a, b, x))

        expected = a_cpu + b
        testing.assert_array_equal(x, expected)

    def test_numpy_scalar(self):
        code = '''
extern "C" __global__ void test_kernel(const double* a, double b, double* x) {
  int i = threadIdx.x;
  x[i] = a[i] + b;
}
'''

        a_cpu = numpy.arange(24, dtype=numpy.float64).reshape((4, 6))
        a = cupy.array(a_cpu)
        b = numpy.float64(2)
        x = cupy.empty_like(a)

        func = _compile_func('test_kernel', code)

        func.linear_launch(a.size, (a, b, x))

        expected = a_cpu + b
        testing.assert_array_equal(x, expected)

    def test_numpy_dtype(self):
        code = '''
extern "C" __global__ void test_kernel(const double* a, double3 b, double* x) {
  int i = threadIdx.x;
  x[i] = a[i] + b.x + b.y + b.z;
}
'''

        double3 = numpy.dtype({'names': ['x', 'y', 'z'],
                               'formats': [numpy.float64]*3})
        a_cpu = numpy.arange(24, dtype=numpy.float64)
        a = cupy.array(a_cpu)
        b = numpy.random.rand(3).view(double3)
        x = cupy.empty_like(a)

        func = _compile_func('test_kernel', code)

        func.linear_launch(a.size, (a, b, x))

        expected = a_cpu + b['x'] + b['y'] + b['z']
        testing.assert_array_equal(x, expected)

    def test_static_array(self):
        code = '''
struct double5 {
    double value[5];
    __device__ const double& operator[](size_t i) const { return value[i]; }
};

extern "C" __global__ void test_kernel(const double* a, double5 b, double* x) {
  int i = threadIdx.x;
  x[i] = a[i] + b[0] + b[1] + b[2] + b[3] + b[4];
}
'''

        a_cpu = numpy.arange(24, dtype=numpy.float64)
        a = cupy.array(a_cpu)
        b = numpy.arange(5).astype(numpy.float64)
        x = cupy.empty_like(a)

        func = _compile_func('test_kernel', code)

        func.linear_launch(a.size, (a, b, x))

        expected = a_cpu + b.sum()
        testing.assert_array_equal(x, expected)

    def test_custom_user_struct(self):
        struct_definition = '''
struct custom_user_struct {
    int4 a;
    char b;
    double c[2];
    short1 d;
    unsigned long long int e[3];
};
'''

        # first step is to determine stuct memory layout
        struct_layout_code = '''
{struct_definition}
extern "C" __global__ void get_struct_layout(size_t* itemsize,
                                size_t *sizes, ptrdiff_t *offsets) {{
    const custom_user_struct* ptr = NULL;

    itemsize[0] = sizeof(custom_user_struct);

    sizes[0] = sizeof(ptr->a);
    sizes[1] = sizeof(ptr->b);
    sizes[2] = sizeof(ptr->c);
    sizes[3] = sizeof(ptr->d);
    sizes[4] = sizeof(ptr->e);

    offsets[0] = (ptrdiff_t)&ptr->a;
    offsets[1] = (ptrdiff_t)&ptr->b;
    offsets[2] = (ptrdiff_t)&ptr->c;
    offsets[3] = (ptrdiff_t)&ptr->d;
    offsets[4] = (ptrdiff_t)&ptr->e;
}}
'''.format(struct_definition=struct_definition)

        itemsize = cupy.ndarray(shape=(1,), dtype=numpy.uint64)
        sizes = cupy.ndarray(shape=(5,), dtype=numpy.uint64)
        offsets = cupy.ndarray(shape=(5,), dtype=numpy.int64)
        func = _compile_func('get_struct_layout', struct_layout_code)
        func.linear_launch(1, (itemsize, sizes, offsets))

        # Build structure data type recursively
        names = list('abcde')
        itemsize = cupy.asnumpy(itemsize).item()
        sizes = cupy.asnumpy(sizes).tolist()
        offsets = cupy.asnumpy(offsets).tolist()

        def mkdtype(basetype, N, itemsize):
            assert 0 < N <= 4, N
            names = list('xyzw')[:N]
            formats = [basetype]*N
            return numpy.dtype(dict(names=names,
                                    formats=formats,
                                    itemsize=itemsize))

        # structure member data types
        int4 = mkdtype(numpy.int32, 4, sizes[0])
        char = mkdtype(numpy.int8, 1, sizes[1])
        double2 = mkdtype(numpy.float64, 2, sizes[2])
        short1 = mkdtype(numpy.int16, 1, sizes[3])
        ulong3 = mkdtype(numpy.uint64, 3, sizes[4])

        formats = [int4, char, double2, short1, ulong3]
        struct_dtype = numpy.dtype(dict(names=names,
                                        formats=formats,
                                        offsets=offsets,
                                        itemsize=itemsize))

        s = numpy.empty(shape=(1,), dtype=struct_dtype)
        s['a'] = numpy.arange(0, 4).astype(numpy.int32).view(int4)
        s['b'] = numpy.arange(4, 5).astype(numpy.int8).view(char)
        s['c'] = numpy.arange(5, 7).astype(numpy.float64).view(double2)
        s['d'] = numpy.arange(7, 8).astype(numpy.int16).view(short1)
        s['e'] = numpy.arange(8, 11).astype(numpy.uint64).view(ulong3)

        # test kernel code
        code = '''
{struct_definition}
extern "C" __global__ void test_kernel(const double* a,
                                       custom_user_struct s,
                                       double* x) {{
    int i = threadIdx.x;
    double sum = s.a.x + s.a.y + s.a.z + s.a.w;
    sum += s.b;
    sum += s.c[0] + s.c[1];
    sum += s.d.x;
    sum += s.e[0] + s.e[1] + s.e[2];
    x[i] = a[i] + sum;
}}
'''.format(struct_definition=struct_definition)

        a_cpu = numpy.arange(24, dtype=numpy.float64)
        a = cupy.array(a_cpu)
        x = cupy.empty_like(a)

        func = _compile_func('test_kernel', code)
        func.linear_launch(a.size, (a, s, x))

        expected = a_cpu + 55.0
        testing.assert_array_equal(x, expected)
