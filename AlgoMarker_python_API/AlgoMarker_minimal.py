import ctypes, json, traceback, os
from functools import wraps

class AlgoMarker:
    """AlgoMarker object that holds full model pipeline to calculate meaningfull insights from EMR raw data.

        Methods
        -------
        calculate
            recieves a request for execution of the model pipeline and returns a responde
        discovery
            returns a json specification of the AlgoMarker information, inputs, etc.
        dispose
            Release object memory - recomanded to use "with" statement
    """
    def __test_not_disposed(func):
        @wraps(func)
        def wrapper(*args):
            s_obj = args[0]
            if s_obj.__disposed:
                raise NameError(
                    f"Error - Can't call {func.__name__} after algomarker was disposed"
                )
            return func(*args)

        return wrapper

    @staticmethod
    def __load_am_lib(libpath : str):
    # Load the shared library into ctypes
        c_lib = ctypes.CDLL(libpath)
        c_lib.AM_API_Create.argtypes = (ctypes.c_int32 ,ctypes.POINTER(ctypes.c_void_p))
        c_lib.AM_API_Load.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_char))
        c_lib.AM_API_DisposeAlgoMarker.argtypes = [ctypes.c_void_p]
        c_lib.AM_API_DisposeAlgoMarker.restype = None
        c_lib.AM_API_AddData.argtypes = (ctypes.c_void_p,ctypes.c_int32 ,ctypes.POINTER(ctypes.c_char) ,ctypes.c_int32,
                                         ctypes.POINTER(ctypes.c_long),ctypes.c_int32 ,ctypes.POINTER(ctypes.c_float))
        c_lib.AM_API_Discovery.argtypes = ( ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p) )
        c_lib.AM_API_Discovery.restype = None
        c_lib.AM_API_GetName.argtypes = ( ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p) )
        
        c_lib.AM_API_ClearData.argtypes = [ ctypes.c_void_p ]
        c_lib.AM_API_AddDataByType.argtypes = ( ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p) )
        c_lib.AM_API_CalculateByType.argtypes = ( ctypes.c_void_p, ctypes.c_int32, ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p) )
        c_lib.AM_API_Dispose.argtypes = [ ctypes.c_char_p ]
        c_lib.AM_API_Dispose.restype = None
        
        return c_lib
    
    @staticmethod
    def create_request_json(patient_id : int, prediction_time : int) -> str:
        """Creates and returns a string json request for patient_id and prediction_time"""
        js_req='{"type": "request", "request_id": "REQ_ID_1234", '+ \
        '"export": {"prediction": "pred_0"}, "requests": [ ' + \
        '{"patient_id":"%d", "time": "%d"} ]}'%(int(patient_id), int(prediction_time))
        return js_req
    
    def __init__(self, amconfig_path :str, libpath : str=None):
        """AlgoMarker constractor - receives AlgoMarker configuration file path "amconfig".
           Optional path to C shared library file. If we want to use other version, not default
           library that is packed in this module.
        """
        if libpath is None:
            libpath=os.path.join(os.path.dirname(os.path.abspath(__file__)),'libdyn_AlgoMarker.so')
        self.__lib=None
        self.__lib = AlgoMarker.__load_am_lib(libpath)
        self.__libpath=libpath
        print(f'Loaded library from {self.__libpath}')
        self.__obj = ctypes.c_void_p()
        res=self.__lib.AM_API_Create(1, ctypes.pointer(self.__obj))
        if res!=0:
            print('Error in creating AlgoMarker object')
        self.__disposed=False
        self.__name=None
        self.__amconfig_path=amconfig_path
        self.__load_algomarker(amconfig_path)
    
    def __load_algomarker(self, amconfig_path : str):
        if not(os.path.exists(amconfig_path)):
            raise NameError(f'amconfig path "{amconfig_path}" not found. File Not Found')
        am_path = ctypes.create_string_buffer(amconfig_path.encode('ascii'))
        res=self.__lib.AM_API_Load(self.__obj, am_path)
        if res!=0:
            raise NameError(f'Error in loading AlgoMarker: {res}')
        else:
            try:
                info_js=self.discovery()
                if 'name'in info_js:
                    self.__name=info_js['name']
                    print(f'Loaded {self.__name} AlgoMarker succefully')
            except:
                print('Warning: couldn\'t retrieve AlgoMarker Name')
    
    def __repr__(self):
        if self.__disposed:
            return f'AlgoMarker was loaded with library {self.__libpath} and amconfig {self.__amconfig_path}, but disposed!'
        if self.__name is not None:
            return f'AlgoMarker {self.__name} was loaded with library {self.__libpath} and amconfig {self.__amconfig_path}'
        else:
            return f'AlgoMarker was loaded with library {self.__libpath} and amcofig {self.__amconfig_path}'
        
    def dispose(self):
        """Disposes the AlgoMarker object and frees the memory"""
        if self.__lib is not None:
            self.__lib.AM_API_DisposeAlgoMarker(self.__obj)
            self.__disposed=True
            if self.__name is None:
                print('Released AlgoMarker object')
            else:
                print(f'Released "{self.__name}" AlgoMarker object')
            self.__lib=None
            self.__obj = None
    def __del__(self):
        self.dispose()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.dispose()
    
    @__test_not_disposed
    def __dispose_string_mem(self, obj):
        self.__lib.AM_API_Dispose(obj)
        
    @__test_not_disposed
    def discovery(self) -> str:
        """Returns information about the Algomarkers in json format - input signals, name, version, etc."""
        res_discovery = ctypes.c_char_p()
        self.__lib.AM_API_Discovery(self.__obj, ctypes.byref( res_discovery))
        try:
            res_discovery_str=res_discovery.value
            #Clear memory:
            self.__dispose_string_mem(res_discovery)
            res_discovery_str=json.loads(res_discovery_str)
            return res_discovery_str
        except:
            print ('Error in discovery json conversion')
            traceback.print_exc()
            return res_discovery_str
    
    @__test_not_disposed
    def __clear_data(self):
        """Frees the algomarker patient data repository"""
        res=self.__lib.AM_API_ClearData(self.__obj)
        if res!=0:
            raise NameError(f'Error in clearing data - error code {res}')
    
    @__test_not_disposed
    def calculate(self, request_json : str) -> str:
        """Recieved json request for calculation and returns json string responde object with the result

           Notes
           -----
           The input json request and json response results are documented in a different document
        """
        self.__clear_data()
        js_req = ctypes.create_string_buffer(request_json.encode('ascii'))
        res_resp = ctypes.c_char_p()
        res=self.__lib.AM_API_CalculateByType(self.__obj,3001, js_req, ctypes.byref( res_resp))
        if res!=0:
            print(f'Calculate Failed {res}')
        try:
            res_resp_str=res_resp.value
            self.__dispose_string_mem(res_resp)
            res_resp_str=json.loads(res_resp_str)
            return res_resp_str
        except:
            print('Error in converting respond json in calculate')
            traceback.print_exc()
            return res_resp_str

#Old API testing
#bdate=(ctypes.c_long * 1)(*[1988])
#bdate_right=(ctypes.c_float * 1)(*[19880327])
#am.lib.AM_API_AddData(am.obj,1,ctypes.create_string_buffer(b"BDATE"),1, bdate,0 ,ctypes.POINTER(ctypes.c_float)())
#am.lib.AM_API_AddData(am.obj,1,ctypes.create_string_buffer(b"BDATE"),0, ctypes.POINTER(ctypes.c_long)(),1 ,bdate_right)
