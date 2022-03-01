# -*- coding: utf-8 -*-
import arcpy
import pandas as pd
import sklearn.cluster
import os
import math
import glob
from arcpy.sa import *

arcpy.env.workspace = "C:\\Users\\zhang\\Desktop\\pop_data"  # 重新设置工作环境似乎会导致错误
originalData = "C:\\Users\\zhang\\Desktop\\pop_data"
Output_Workspace = "C:\\Users\\zhang\\Desktop\\pop_data\\point_data"
HH_Workspace = "C:\\Users\\zhang\\Desktop\\pop_data\\HH"
Select_Workspace = "C:\\Users\\zhang\\Desktop\\pop_data\\HH\\select"
Calculation_Workspace = "C:\\Users\\zhang\\Desktop\\pop_data\\pop_data_select"
Empty_Workspace = "C:\\Users\\zhang\\Desktop\\pop_data\\empty"
Distance_Workspace = "C:\\Users\\zhang\\Desktop\\pop_data\\pop_data_select\\distance"

# 按照国家行政边界裁剪原始栅格数据
arcpy.CheckOutExtension('Spatial')  # 检索arcpy许可管理器中的拓展模块是否可用
inputPath = "C:\\Users\\zhang\\Desktop\\pop_data\\pop2000_2018"
outputPath = "C:\\Users\\zhang\\Desktop\\pop_data\\pop2000_2018\\city"
# 指定shp范围边界文件，即目标区域的掩膜
mask = "C:\\Users\\zhang\\Desktop\\pop_data\\pop_data\\pop2000_2018\\city.shp"
# 利用glob包，将inputpath下的所有tif文件读存放到rasters中
rasters = glob.glob(os.path.join(inputPath, "*.tif"))
# 循环rasters中的所有影像，进行按掩模提取操作
for ras in rasters:
    name = os.path.basename(ras) + "_ebm.tif"
    outName = os.path.join(outputPath, name)  # 合并输出文件名+输出路径
    out_extract = arcpy.sa.ExtractByMask(ras, mask)  # 执行按掩模提取操作
    out_extract.save(outName)  # 保存数据
print "         ---- 全部裁剪完成 ----         "

# shp文件按属性分割为多个shp
shpFile = "C:\\Users\\zhang\\Desktop\\pop_data\\pop2000_2018\\city_pro.shp"  # 要处理的省级shp文件路径
outPath = "C:\\Users\\zhang\\Desktop\\pop_data\\pop2000_2018\\cityShpSeparate"  # 输出各个省的文件路径

with arcpy.da.SearchCursor(shpFile, ["SHAPE@", "ID"]) as cursor:
    # SHAPE@指代单个要素，ID是一个字段，该字段也是我们想要作为每个polygon命名的值，不能使用中文
    for row in cursor:
        out_name = str(row[1]) + '.shp'  # 输出文件名 确保均为字符串类型，row[1]为“ID”在元组中的位置
        arcpy.FeatureClassToFeatureClass_conversion(row[0], outPath, out_name)
print "         ---- 全部shp分割完成 ----         "

# 循环按照各个省shp文件裁剪不同时段的多个tif
arcpy.CheckOutExtension("ImageAnalyst")
arcpy.CheckOutExtension("spatial")
outPath = "C:\\Users\\zhang\\Desktop\\pop_data\\pop2000_2018\\cityTifSeparate"

# 定义工作空间及数据路径，路径下有各省shp文件以及全国不同时段tif文件
rasters = arcpy.ListRasters("*", "tif")  # 遍历工作空间中的tif格式数据
inMasks = arcpy.ListFeatureClasses()  # 遍历工作空间中的shp格式数据
for inMask in inMasks:
    for raster in rasters:
        outExtract = ExtractByMask(raster, inMask)  # 批量裁剪文件
        outExtract.save(outPath + os.sep + str(raster).replace('.tif', '') + "_" + str(inMask).replace('.shp', '') + ".tif")  # 输出存储裁剪的栅格数据，存储到新建文件夹里
print "         ---- 遥感影像按全部shp分割完成 ----         "

# 栅格要素转点，尽可能转为投影坐标系，否则像元经度差在高低纬度有剧烈变化
filenames = os.listdir(originalData)
for filename in filenames:
    if os.path.splitext(filename)[1] == ".tif":
        inRaster = originalData + os.sep + filename
        basename = os.path.splitext(filename)[0] + "_Point"
        outPoint = Output_Workspace + os.sep + basename + ".shp"
        field = "VALUE"
        arcpy.RasterToPoint_conversion(inRaster, outPoint, field)  # 要素转点工具
print "         ---- 遥感影像全部转为点数据 ----         "

# 计算Anselin Local Moran's I值
filenames = os.listdir(Output_Workspace)
for filename in filenames:
    if os.path.splitext(filename)[1] == ".shp":
        inPoint = Output_Workspace + os.sep + filename
        basenameMoran = os.path.splitext(filename)[0] + "_Moran"
        outPoint = HH_Workspace + os.sep + basenameMoran + ".shp"
        arcpy.ClustersOutliers_stats(inPoint, "grid_code", outPoint, "INVERSE_DISTANCE", "EUCLIDEAN_DISTANCE", "NONE")  # 计算局部空间自相关性
print "         ---- 点数据局部空间自相关检测已完成 ----         "

# 提取HH聚类并计算点数据的坐标
filenames = os.listdir(HH_Workspace)
for filename in filenames:
    if os.path.splitext(filename)[1] == ".shp":
        inPoint = HH_Workspace + os.sep + filename
        basenameSelect = os.path.splitext(filename)[0] + "_HHSelect"
        outPointSelect = Select_Workspace + os.sep + basenameSelect + ".shp"
        outExcel = Select_Workspace + os.sep + basenameSelect + ".xls"
        arcpy.Select_analysis(inPoint, outPointSelect, "COType = 'HH'")
        arcpy.AddField_management(outPointSelect, "X", "FLOAT", field_precision=12, field_scale=5)
        # 注意小数点后位数，使用地理坐标系时需要更高的精度
        arcpy.AddField_management(outPointSelect, "Y", "FLOAT", field_precision=12, field_scale=5)
        arcpy.CalculateField_management(outPointSelect, "X", "!SHAPE.CENTROID.X!", "PYTHON_9.3")
        arcpy.CalculateField_management(outPointSelect, "Y", "!SHAPE.CENTROID.Y!", "PYTHON_9.3")
        arcpy.TableToExcel_conversion(outPointSelect, outExcel)
print "         ---- HH聚类已全部保留 ----         "

# 利用密度聚类识别边连接和点连接的拓扑关系，并按照人口阈值区分聚类结果
filenames = os.listdir(Select_Workspace)
for filename in filenames:
    if os.path.splitext(filename)[1] == ".xls":
        inExcel = Select_Workspace + os.sep + filename
        basenameCluster = os.path.splitext(filename)[0] + "_Connect"
        outCluster = Calculation_Workspace + os.sep + basenameCluster + ".xls"
        outClusterEmpty = Empty_Workspace + os.sep + "Empty" + "_" + basenameCluster + ".xls"
        data = pd.read_excel(inExcel, encoding="utf-8")
        X = data[["X", "Y"]]
        dbscanModel = sklearn.cluster.DBSCAN(eps=1200, min_samples=1, metric="euclidean")  # 利用聚类方法区分边连接和点连接，设置最小样本数为1，监测范围为(1,2^0.5)之间的任意值
        dbscanModel.fit(X)
        clusterResult = pd.concat([data, pd.Series(dbscanModel.labels_, index=data.index)], axis=1, names="types")
        clusterResultRevise = clusterResult.drop(
            ["SOURCE_ID", "LMiIndex", "LMiZScore", "LMiPValue", "COType", "NNeighbors"], axis=1).rename(
            columns={0: "cluster"})
        popSum = clusterResultRevise.groupby('cluster')['grid_code'].sum()
        popSum = pd.DataFrame(popSum)
        popSum["cluster"] = popSum.reset_index().index
        maxPop = popSum["grid_code"].max()
        if maxPop >= 50000:
            popSum2 = popSum[popSum.grid_code >= 50000]
            popSum2 = popSum2.copy()
            popSum2["type"] = "SemiCenter"
            popSum2 = popSum2.sort("grid_code", ascending=False)
            popSum2.iat[0, 2] = "MainCenter"
            clusterNumber = popSum2['cluster'].unique()
            clusterResultDelete = clusterResultRevise[
                pd.DataFrame(clusterResultRevise.cluster.tolist()).isin(clusterNumber).any(1).values]
            clusterResultUpdate = clusterResultDelete
            clusterResultUpdate = clusterResultUpdate.copy()
            clusterResultUpdate["type"] = "SemiCenter"
            for i in range(len(clusterResultUpdate)):
                for j in range(len(popSum2)):
                    if clusterResultUpdate.iat[i, 4] == popSum2.iat[j, 1]:
                        clusterResultUpdate.iat[i, 1] = popSum2.iat[j, 0]
                        clusterResultUpdate.iat[i, 5] = popSum2.iat[j, 2]
            clusterResultUpdate.to_excel(outCluster, index=False)
        else:
            popSum.to_excel(outClusterEmpty, index=False)
print "         ---- 主要、次要中心及人口已全部识别 ----         "

# 计算聚类之间的最短欧氏距离
filenames = os.listdir(Calculation_Workspace)
for filename in filenames:
    if os.path.splitext(filename)[1] == ".xls":
        inExcel = Calculation_Workspace + os.sep + filename
        basenameDistance = os.path.splitext(filename)[0] + "_Distance"
        outDistance = Distance_Workspace + os.sep + basenameDistance + ".xls"
        connectPoint = pd.read_excel(inExcel)
        mainCenter = connectPoint[connectPoint["type"] == "MainCenter"]
        mainCenterNumber = mainCenter.iat[0, 4]
        semiCenter = connectPoint[connectPoint["type"] == "SemiCenter"]
        clusterNames = semiCenter['cluster'].unique()
        distanceResult = pd.DataFrame(columns=["mainCenter", "semiCenter", "distance"])  # 初始集放在循环之外
        for x in clusterNames:
            semiCenterX = semiCenter[semiCenter["cluster"] == x]
            distance2 = math.sqrt(math.pow((mainCenter.iat[0, 2] - semiCenterX.iat[0, 2]), 2) + math.pow(
                (mainCenter.iat[0, 3] - semiCenterX.iat[0, 3]), 2))
            for a in range(len(mainCenter)):
                for b in range(len(semiCenterX)):
                    distance1 = math.sqrt(math.pow((mainCenter.iat[a, 2] - semiCenterX.iat[b, 2]), 2) + math.pow(
                        (mainCenter.iat[a, 3] - semiCenterX.iat[b, 3]), 2))
                    if distance1 < distance2:
                        distance2 = distance1
            row = pd.Series([mainCenterNumber, x, distance2])
            row.index = ["mainCenter", "semiCenter", "distance"]
            distanceResult = distanceResult.append(row, ignore_index=True)
        distanceResult.to_excel(outDistance, index=False)
print "         ---- 主要次要中心距离已全部导出 ----         "
