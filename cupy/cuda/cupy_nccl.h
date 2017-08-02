// This file is a stub header file of cudnn for Read the Docs.

#ifndef INCLUDE_GUARD_CUPY_NCCL_H
#define INCLUDE_GUARD_CUPY_NCCL_H

#ifndef CUPY_NO_CUDA

#include <nccl.h>

#else // #ifndef CUPY_NO_CUDA

extern "C" {

typedef struct ncclComm* ncclComm_t;

enum {
    NCCL_UNIQUE_ID_BYTES = 128
};
typedef struct {
    char internal[NCCL_UNIQUE_ID_BYTES];
} ncclUniqueId;

typedef enum {
    ncclSuccess
} ncclResult_t;

typedef enum {} ncclRedOp_t;

typedef enum {} ncclDataType_t;

const char* ncclGetErrorString(...);
ncclResult_t ncclGetUniqueId(...);
ncclResult_t ncclCommInitRank(...);
void ncclCommDestroy(...);
ncclResult_t ncclCommCuDevice(...);
ncclResult_t ncclCommUserRank(...);
ncclResult_t ncclAllReduce(...);
ncclResult_t  ncclReduce(...);
ncclResult_t  ncclBcast(...);

}

#endif // #ifndef CUPY_NO_CUDA

#ifndef NCCL_MAJOR
#define NCCL_MAJOR 1
#define NCCL_MINOR 0
#define NCCL_PATCH 0
#endif

#define NCCL_VERSION  (NCCL_MAJOR * 1000 + NCCL_MINOR * 100 + NCCL_PATCH)

#endif // #ifndef INCLUDE_GUARD_CUPY_NCCL_H
