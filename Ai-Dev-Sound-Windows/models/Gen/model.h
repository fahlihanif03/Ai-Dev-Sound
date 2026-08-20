/*
* DEEPCRAFT Studio 5.14.5788.0+51541183f4b9ca433a12c0d5c3809d9a54d31f3c
* Copyright © 2023- Imagimob AB, All Rights Reserved.
* 
* Generated at 08/20/2026 07:35:23 UTC. Any changes will be lost.
* 
* Memory    Size                      Efficiency
* Buffers   12296 bytes (RAM)         100 %
* State     14896 bytes (RAM)         100 %
* Readonly  2383144 bytes (Flash)     100 %
* 
* Backend              tensorflow
* Keras Version        2.20.1
* Backend Model Type   Functional
* Backend Model Name   fan_autoencoder
* 
* Layer                          Shape           Type       Function
* Sliding Window (data points)   [1024]          float      dequeue
*    window_shape = [1024]
*    stride = 512
*    buffer_multiplier = 1
* Hamming smoothing              [1024]          float      dequeue
*    sym = True
* Real Discrete Fourier Transform [513,2]         float      dequeue
*    axis = 0
* Frobenius norm                 [513]           float      dequeue
*    axis = 0
* Mel Filterbank                 [64]            float      dequeue
*    num_filters = 64
*    sample_rate = 16000
*    f_low = 0
*    f_high = 8000
* Add Constant                   [64]            float      dequeue
*    A = 1
* Logarithm                      [64]            float      dequeue
* Clip                           [64]            float      dequeue
*    min = 0
*    max = 4
* Imagimob Speech Features       [64]            float      dequeue
*    output_freq = 31.25
*    output_features = 64
*    low_cut_freq = 0
*    high_cut_freq = 8000
* Sliding Window (data points)   [32,64]         float      dequeue
*    window_shape = [32,64]
*    stride = 64
*    buffer_multiplier = 1
* Contextual Window (Sliding Window) [32,64]         float      dequeue
*    contextual_length_sec = 1.024
*    prediction_freq = 31.25
* Reshape                        [2048]          float      dequeue
*    shape = [2048]
* Input Layer                    [2048]          float      dequeue
*    shape = [2048]
* Dense                          [128]           float      dequeue
*    units = 128
*    use_bias = True
*    activation = relu
*    trainable = True
*    weight = float[2048,128]
*    bias = float[128]
* Dense                          [128]           float      dequeue
*    units = 128
*    use_bias = True
*    activation = relu
*    trainable = True
*    weight = float[128,128]
*    bias = float[128]
* Dense                          [128]           float      dequeue
*    units = 128
*    use_bias = True
*    activation = relu
*    trainable = True
*    weight = float[128,128]
*    bias = float[128]
* Dense                          [8]             float      dequeue
*    units = 8
*    use_bias = True
*    activation = relu
*    trainable = True
*    weight = float[128,8]
*    bias = float[8]
* Dense                          [128]           float      dequeue
*    units = 128
*    use_bias = True
*    activation = relu
*    trainable = True
*    weight = float[8,128]
*    bias = float[128]
* Dense                          [128]           float      dequeue
*    units = 128
*    use_bias = True
*    activation = relu
*    trainable = True
*    weight = float[128,128]
*    bias = float[128]
* Dense                          [128]           float      dequeue
*    units = 128
*    use_bias = True
*    activation = relu
*    trainable = True
*    weight = float[128,128]
*    bias = float[128]
* Dense                          [2048]          float      dequeue
*    units = 2048
*    use_bias = True
*    activation = linear
*    trainable = True
*    weight = float[128,2048]
*    bias = float[2048]
* 
* Exported functions:
* 
* int IMAI_dequeue(float *restrict data_out)
*    Description: Dequeue features. RET_SUCCESS (0) on success, RET_NODATA (-1) if no data is available, RET_NOMEM (-2) on internal memory error
*    Parameter data_out is Output of size float[2048].
* 
* int IMAI_enqueue(const float *restrict data_in)
*    Description: Enqueue features. Returns SUCCESS (0) on success, else RET_NOMEM (-2) when low on memory.
*    Parameter data_in is Input of size float[1].
* 
* void IMAI_init(void)
*    Description: Initializes buffers to initial state. This function also works as a reset function.
* 
* 
* Disclaimer:
*   The generated code relies on the optimizations done by the C compiler.
*   For example many for-loops of length 1 must be removed by the optimizer.
*   This can only be done if the functions are inlined and simplified.
*   Check disassembly if unsure.
*   tl;dr Compile using gcc with -O3 or -Ofast
*/

#ifndef _IMAI_MODEL_H_
#define _IMAI_MODEL_H_
#ifdef _MSC_VER
#pragma once
#endif

#include <stdint.h>
#define IMAI_API_QUEUE

// First nibble is bit encoding, second nibble is number of bytes
#define IMAGINET_TYPES_NONE	(0x0)
#define IMAGINET_TYPES_FLOAT32	(0x14)
#define IMAGINET_TYPES_FLOAT64	(0x18)
#define IMAGINET_TYPES_INT8	(0x21)
#define IMAGINET_TYPES_INT16	(0x22)
#define IMAGINET_TYPES_INT32	(0x24)
#define IMAGINET_TYPES_INT64	(0x28)
#define IMAGINET_TYPES_QDYN8	(0x31)
#define IMAGINET_TYPES_QDYN16	(0x32)
#define IMAGINET_TYPES_QDYN32	(0x34)

// data_in [1] (4 bytes)
#define IMAI_DATA_IN_COUNT (1)
#define IMAI_DATA_IN_TYPE float
#define IMAI_DATA_IN_TYPE_ID IMAGINET_TYPES_FLOAT32
#define IMAI_DATA_IN_SCALE (1)
#define IMAI_DATA_IN_OFFSET (0)
#define IMAI_DATA_IN_IS_QUANTIZED (0)

// data_out [2048] (8192 bytes)
#define IMAI_DATA_OUT_COUNT (2048)
#define IMAI_DATA_OUT_TYPE float
#define IMAI_DATA_OUT_TYPE_ID IMAGINET_TYPES_FLOAT32
#define IMAI_DATA_OUT_SCALE (1)
#define IMAI_DATA_OUT_OFFSET (0)
#define IMAI_DATA_OUT_IS_QUANTIZED (0)

#define IMAI_KEY_MAX (57)



// Return codes
#define IMAI_RET_SUCCESS 0
#define IMAI_RET_NODATA -1
#define IMAI_RET_NOMEM -2

// Exported methods
int IMAI_dequeue(float *restrict data_out);
int IMAI_enqueue(const float *restrict data_in);
void IMAI_init(void);

#endif /* _IMAI_MODEL_H_ */
