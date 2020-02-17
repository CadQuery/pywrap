find_path( OPENCASCADE_INCLUDE_DIR Standard.hxx PATHS
           $ENV{CONDA_PREFIX}/include/opencascade )

set ( OCCT_MODULES 
    TKMath 
    TKernel 
    TKG2d 
    TKG3d 
    TKGeomBase 
    TKBRep 
    TKGeomAlgo 
    TKTopAlgo 
    TKPrim 
    TKShHealing 
    TKHLR 
    TKMesh 
    TKBO 
    TKBool 
    TKFeat 
    TKOffset 
    TKFillet 
    TKGeomAlgo 
    TKHLR 
    TKMesh 
    TKOffset 
    TKPrim 
    TKShHealing 
    TKTopAlgo 
    TKXMesh 
    TKXSBase 
    TKService 
    TKV3d 
    TKOpenGl 
    TKMeshVS 
    TKBin 
    TKBinL 
    TKBinTObj 
    TKCAF 
    TKCDF 
    TKLCAF 
    TKStd 
    TKStdL 
    TKTObj 
    TKVCAF 
    TKXml 
    TKXmlL 
    TKXmlTObj 
    TKIGES 
    TKSTEP 
    TKSTEP209 
    TKSTEPAttr 
    TKSTEPBase 
    TKSTL 
    TKXSBase )
 
foreach( MOD ${OCCT_MODULES})
     find_library( OPENCASCADE_LIB_${MOD} NAMES ${MOD} PATHS $ENV{CONDA_PREFIX}/lib )
     list( APPEND OPENCASCADE_LIBRARIES ${OPENCASCADE_LIB_${MOD}} )
     mark_as_advanced( OPENCASCADE_LIB_${MOD} )
endforeach()


add_library( OPENCASCADE IMPORTED INTERFACE)
set_target_properties( OPENCASCADE PROPERTIES 
                       INTERFACE_INCLUDE_DIRECTORIES ${OPENCASCADE_INCLUDE_DIR}
                       INTERFACE_LINK_LIBRARIES "${OPENCASCADE_LIBRARIES}" )


include( FindPackageHandleStandardArgs )
find_package_handle_standard_args( OCCT DEFAULT_MSG OPENCASCADE_LIBRARIES OPENCASCADE_INCLUDE_DIR )