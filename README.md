## Installations
Those are installation steps required for all tools and builds:
### 1. Install Compiler and Build Tools (Ubuntu)
To install the essential compiler and build tools, run:
```bash
sudo apt install binutils gcc g++ cmake make swig -y
```
### 2. Install OpenMP Support (Ubuntu)
To enable OpenMP (used for parallel processing), install the following package:
```bash
sudo apt install libgomp1 -y
```
### 3. Install Boost Libraries (Ubuntu)
To install the required Boost components, on Ubuntu 24.04 use:
```bash
sudo apt install libboost-system1.83-dev libboost-filesystem1.83-dev libboost-regex1.83-dev libboost-program-options1.83-dev -y
```
> [!NOTE] On Ubuntu 22.04, Boost version 1.74 is available and is also compatible.
You may also choose to [download and compile Boost manually](https://www.boost.org/users/download/) if you prefer a different version. This project has been tested with Boost versions 1.67 through 1.85, and should work with other versions as well.


### To Build Wrapper for Algomarker please run:
1. Install Boost libraries (as desribed in #3), or edit ```MR_Tools/AlgoMarker_python_API/ServerHandler/CMakeLists.txt``` and point to Boost compile path in variable: ```BOOST_ROOT```
2. Execute:
```bash
MR_Tools/AlgoMarker_python_API/ServerHandler/compile.sh
```

### To build all tools:
1. Install Boost libraries (as desribed in #3), or edit ```MR_Tools/AlgoMarker_python_API/ServerHandler/CMakeLists.txt``` and point to Boost compile path in variable: ```BOOST_ROOT```
2. Get [Medial Libs](https://github.com/alonmedial/MR_LIBS) Clone it to somewhere in your computer
3. Store the path in ```MR_Tools/All_Tools/CMakeLists.txt``` edit this line ```SET(LIBS_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../../MR_LIBS")``` to point this path, the default is folder next to MR_Tools with the name MR_LIBS
4. Execute:
   ```bash
   AllTools/full_build.sh
   ```
