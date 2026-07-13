// @ts-nocheck
// /////////////////////////////////////////////
//	Last Modified: 2025-08-12 13:27:00
// /////////////////////////////////////////////

// /////////////////////////////////////////////
//	GUIP Module Control
// /////////////////////////////////////////////
var guipControl;

/** 判断是否在GUIP CEF内 */
var IS_GUIP = (guipControl !== null && guipControl !== undefined);

/** 判断是否为FIREFOX */
var BROWSER_IS_FF = navigator && navigator.userAgent && navigator.userAgent.includes('Firefox/');

/** 判断是否为360ENT */
var BROWSER_IS_360ENT = navigator && navigator.userAgent && navigator.userAgent.includes('QIHU 360ENT');

/** 判断是否发生点击事件 */
var DOM_HAS_CLICKED = false;

/** close超时等待时间 */
var CLOSE_MODULE_TIMEOUT = 5000;

function _detectDomHasClicked(e) {
  DOM_HAS_CLICKED = true;
  window.removeEventListener('click', _detectDomHasClicked);
}
function _detectDomHasClickedAfterLoaded(e) {
  window.addEventListener('click', _detectDomHasClicked);
}
!IS_GUIP && window.addEventListener('load', _detectDomHasClickedAfterLoaded);

/**
 * 生成模块uid
 */
function _genarateModuleID() {
  let d = new Date().getTime();
  let uid = 'uid-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'.replace(/[x]/g, function (c) {
    var r = (d + Math.random() * 16) % 16 | 0;
    d = Math.floor(d / 16);
    return (c == 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
  return uid + '';
}

function _appendURLWithModuleData(basicURL, moduleData = {}, query) {
  var hash = '';
  var sharpIndex = basicURL.lastIndexOf('#');
  if (sharpIndex > 0) {
    hash = basicURL.substr(sharpIndex);
  }
  var basicURLObj = null;
  if (basicURL.startsWith('http:') || basicURL.startsWith('https:')) {
    basicURLObj = new URL(hash, basicURL);
  } else {
    basicURLObj = new URL(basicURL, window.location.href);
  }
  basicURLObj.searchParams.set('moduleData', JSON.stringify(moduleData));
  basicURLObj.searchParams.set('guipToken', getGuipToken() || '');
  basicURLObj.searchParams.set('guipToken2', getGuipToken2() || '');
  basicURLObj.searchParams.set('guwpToken', getGuwpToken() || '');
  var oaheader = _getSearchParams().get('oaheader');
  if (oaheader) {
    basicURLObj.searchParams.set('oaheader', oaheader);
  }
  if (query) {
    for (const key in query) {
      if (query[key] !== null && query[key] !== undefined) {
        basicURLObj.searchParams.set(key, query[key]);
      }
    }
  }
  return basicURLObj.toString();
}

/**
 * 弹出授权组件
 * @param {*} id
 * @param {*} level
 * @param {*} funcCode
 */
function startAccredit(id, level, funcCode) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.startAccredit(id, level, funcCode);
    return;
  }
  // TODO H5如何调用？
}

/**
 * 取消授权
 */
function remoteAccredit() {
  if (guipControl != null && guipControl != undefined) {
    guipControl.remoteAccredit();
    return;
  }
  // TODO H5如何调用？
}

function _getFuncByCode(funcCode) {
  return (globalInfo().funcCodeFullMap || {})[funcCode];
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 根据功能码获取功能名称
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {string} funcCode
 * @param {function} callback
 */
function getFuncNameByFuncCode(funcCode, callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getFuncNameByFuncCode(callback, funcCode);
  } else {
    var funcVo = _getFuncByCode(funcCode);
    if (!funcVo) {
      callback(funcCode);
    } else {
      callback(funcVo.funcName);
    }
  }
}

function _getAppByCode(appCode) {
  return (globalInfo().appList || []).find((appVo) => appVo.appCode === appCode);
}

function _getAppById(appId) {
  return (globalInfo().appList || []).find((appVo) => appVo.appId === appId);
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 根据功能码获取功能名称
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {string} appCode
 * @param {function} callback
 */
function getRootUrlByAppCode(appCode, callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getRootUrlByAppCode(callback, appCode);
  } else {
    promise._getAppByCode(appCode).then((appVo) => {
      if (appVo) {
        callback(appVo.appRootUrl);
      } else {
        callback(null);
      }
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 根据功能码获取路径
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {string} funcCode
 * @param {function} callback
 */
function getUrlByFuncCode(funcCode, callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getUrlByFuncCode(callback, funcCode);
  } else {
    promise._getFuncByCode(funcCode).then((funcVo) => {
      var funcUrl = '';
      if (funcVo) {
        funcUrl = funcVo.funcUrl;
        if (funcUrl && (funcUrl.startsWith('http://') || funcUrl.startsWith('https://'))) {
          callback(funcUrl);
          return;
        } else {
          promise._getAppById(funcVo.appId).then((appVo) => {
            funcUrl = appVo ? (appVo.appRootUrl + funcUrl) : funcUrl;
            callback(funcUrl);
          });
          return;
        }
      }
      callback(funcUrl);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取所属模块 id
 * @param {function} callback
 */
function getDocumentModuleId(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getDocumentModuleId(callback);
  } else {
    callback((guipModule || {}).moduleId);
  }
}


function getIpBranchCode(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getIpBranchCode(callback);
  } else {
    callback('');
  }
}

function getIpOrgCode(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getIpOrgCode(callback);
  } else {
    callback('');
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取移动 E 动终端标识
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {function} callback
 */
function getEMobile(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getEMobile(callback);
  } else {
    promise.globalInfo().then((value) => {
      callback(value.isEMobile);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 港行获取分行会计日期，境内返回accDate
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {function} callback
 */
function getBranchAccDate(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getBranchAccDate(callback);
  } else {
    // TODO 香港分行情况处理
    promise.globalInfo().then((value) => {
      callback(value.accDate);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 港行获取子行会计日期，境内返回accDate
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {function} callback
 */
function getSubAccDate(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getSubAccDate(callback);
  } else {
    // TODO 香港子行情况处理
    promise.globalInfo().then((value) => {
      callback(value.accDate);
    });
  }
}

var _guipPublicAreaDB = null;
var _guipPublicAreaDBName = 'guipPublicArea';
var _guipPublicAreaVersion = 1;
var _guipPublicObj = {};

// ====================
// 数据库基本操作
// ====================
/**
 * 打开数据库
 */
function _openDB() {
  return new Promise((resolve, reject) => {
    if (_guipPublicAreaDB) {
      console.log(`数据库【${_guipPublicAreaDBName}:${_guipPublicAreaVersion}】已打开，不需要重复打开`);
      resolve();
      return;
    }
    const request = window.indexedDB.open(_guipPublicAreaDBName, _guipPublicAreaVersion);
    request.onerror = (event) => {
      console.error(`打开数据库【${_guipPublicAreaDBName}:${_guipPublicAreaVersion}】出现错误`, event);
      reject(new Error(`打开数据库【${_guipPublicAreaDBName}:${_guipPublicAreaVersion}】出现错误`));
    };
    request.onsuccess = () => {
      _guipPublicAreaDB = request.result;
      console.log(`打开数据库【${_guipPublicAreaDBName}:${_guipPublicAreaVersion}】成功`);
      // 清理临时表
      _dbClear('temporary');
      resolve();
    };
    request.onupgradeneeded = (event) => {
      _guipPublicAreaDB = event.target.result;
      _guipPublicAreaDB.onerror = (event) => {
        console.error('数据库出现错误', event);
      };
      console.log('数据库需要升级');
      // 建持久化数据表
      _guipPublicAreaDB.createObjectStore('permanent');
      // 建临时数据表
      _guipPublicAreaDB.createObjectStore('temporary');
    };
  });
}

/**
 * 向数据库插入数据
 * @param {string} tableName 表名
 * @param {*} value 需要插入的数据，不能为空
 * @param {*} key 任意key
 */
function _dbAdd(tableName, value, key) {
  return new Promise((resolve, reject) => {
    const transaction = _guipPublicAreaDB.transaction([tableName], 'readwrite');
    transaction.oncomplete = () => {
      resolve();
    };
    transaction.onerror = (event) => {
      console.error('数据写入失败', event);
      reject('数据写入失败');
    };
    transaction.objectStore(tableName).add(value, key);
  });
}

/**
 * 向数据库插入或更新数据
 * @param {string} tableName 表名
 * @param {*} value 需要插入的数据，不能为空
 * @param {*} key 任意key
 */
function _dbPut(tableName, value, key) {
  return new Promise((resolve, reject) => {
    const transaction = _guipPublicAreaDB.transaction([tableName], 'readwrite');
    transaction.oncomplete = () => {
      resolve();
    };
    transaction.onerror = (event) => {
      console.error('数据写入失败', event);
      reject('数据写入失败');
    };
    transaction.objectStore(tableName).put(value, key);
  });
}

/**
 * 使用key查询数据
 * @param {string} tableName 表名
 * @param {*} key 任意key
 */
function _dbGet(tableName, key) {
  return new Promise((resolve, reject) => {
    const transaction = _guipPublicAreaDB.transaction([tableName]);
    transaction.onerror = (event) => {
      console.error('数据读取失败', event);
      reject('数据读取失败');
    };
    const request = transaction.objectStore(tableName).get(key);
    request.onsuccess = () => {
      resolve(request.result);
    };
  });
}

/**
 * 使用key删除数据
 * @param {string} tableName 表名
 * @param {*} key 任意key
 */
function _dbDelete(tableName, key) {
  return new Promise((resolve, reject) => {
    const transaction = _guipPublicAreaDB.transaction([tableName], 'readwrite');
    transaction.oncomplete = () => {
      resolve();
    };
    transaction.onerror = (event) => {
      console.error('数据删除失败', event);
      reject('数据删除失败');
    };
    transaction.objectStore(tableName).delete(key);
  });
}

/**
 * 清空表
 * @param {string} tableName 表名
 */
function _dbClear(tableName) {
  return new Promise((resolve, reject) => {
    const transaction = _guipPublicAreaDB.transaction([tableName], 'readwrite');
    transaction.oncomplete = () => {
      resolve();
    };
    transaction.onerror = (event) => {
      console.error('清空数据失败', event);
      reject('清空数据失败');
    };
    transaction.objectStore(tableName).clear();
  });
}

function _getTableName(permanent) {
  return permanent ? 'permanent' : 'temporary';
}

/**
 * 添加属性到公共区域，permanent 为是否持久化
 * 在浏览器上，借助indexeddb实现，所以只有同域的页面间才可获取数据
 * @param {function} callback
 */
function put(key, value, permanent) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.put(key, value, permanent);
    return;
  }
  _dbPut(_getTableName(permanent), value, key);
}

/**
 * 从公共区域获取数据，permanent 为是否持久化
 * 在浏览器上，借助indexeddb实现，所以只有同域的页面间才可获取数据
 * @param {function} callback
 */
function get(key, permanent, callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.get(callback, key, permanent);
  } else {
    _dbGet(_getTableName(permanent), key).then((value) => {
      callback(value);
    }).catch((e) => {
      callback(null);
    });
  }
}

/**
 * 删除公共区域获取数据，permanent 为是否持久化
 * 在浏览器上，借助indexeddb实现，所以只有同域的页面间才可获取数据
 * @param {function} callback
 */
function remove(key, permanent) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.remove(key, permanent);
    return;
  }
  _dbDelete(_getTableName(permanent), key);
}

/**
 * 重启GUIP
 * 在浏览器等同于刷新本页面
 */
function restartGuip() {
  if (guipControl != null && guipControl != undefined) {
    guipControl.restartGuip();
    return;
  }
  window.location.reload();
}

// moduleId与被打开的window对象映射
var _moduleIdWinMap = {};
// funcCode与被打开的window对象映射
var _funcCodeWinMap = {};
// 正在被挂起的模块ID清单
var _suspendModuleIdList = [];
// moduleId与openModule传递的大参数映射
var _moduleIdLargeParamMap = {};
// moduleId与回调参数映射
var _moduleIdTransferParamMap = {};

function _beforeUnloadHandler(e) {
  e.preventDefault();
  e.returnValue = '';
}

function _releaseWindowByModuleId(moduleId) {
  if (!moduleId) {
    return false;
  }
  var childWin = _moduleIdWinMap[moduleId];
  if (childWin && !childWin.closed) {
    childWin.close();
  }
  childWin = null;
  delete _moduleIdWinMap[moduleId];
  _suspendModuleIdList = _suspendModuleIdList.filter((value) => value !== moduleId);

  for (var funcCode in _funcCodeWinMap) {
    if (!_funcCodeWinMap.hasOwnProperty(funcCode)) {
      continue;
    }
    _funcCodeWinMap[funcCode] = _funcCodeWinMap[funcCode].filter((value) => value !== moduleId);
  }
}

function _windowExistsByModuleId(moduleId) {
  if (!moduleId) {
    return false;
  }
  var childWin = _moduleIdWinMap[moduleId];
  return childWin && !childWin.closed;
}

function _releaseWindowByFuncCode(funcCode) {
  if (!funcCode || !_funcCodeWinMap[funcCode]) {
    return;
  }
  for (var moduleId of _funcCodeWinMap[funcCode]) {
    _releaseWindowByModuleId(moduleId);
  }
  _funcCodeWinMap[funcCode] = [];
}

function _setIntervalForReleaseWindow() {
  setInterval(() => {
    for (var moduleId in _moduleIdWinMap) {
      if (!_moduleIdWinMap.hasOwnProperty(moduleId)) {
        continue;
      }
      if (!_windowExistsByModuleId(moduleId)) {
        console.log('release module: ', moduleId);
        _releaseWindowByModuleId(moduleId);
      }
    }
  }, 10 * 60 * 1000);
}

!IS_GUIP && _setIntervalForReleaseWindow();

/**
 * 释放回调参数对象
 * @param {string} moduleId 
 */
function _releaseTransferParamByModuleId(moduleId) {
  if (!moduleId || !_moduleIdTransferParamMap[moduleId]) {
    return;
  }
  _moduleIdTransferParamMap[moduleId] = null;
  delete _moduleIdTransferParamMap[moduleId];
}

/**
 * 释放大参数对象
 * @param {string} moduleId 
 */
function _releaseLargeParamByModuleId(moduleId) {
  if (!moduleId || !_moduleIdLargeParamMap[moduleId]) {
    return;
  }
  _moduleIdLargeParamMap[moduleId] = null;
  delete _moduleIdLargeParamMap[moduleId];
}

/**
 * 挂起本页面
 */
function _suspendModule() {
  if (document.getElementById('guip-mask')) {
    console.debug('已存在mask');
    return;
  }
  var baseStyle = 'z-index: 10000; top: 0; bottom: 0; left: 0; right: 0; position: fixed;';
  var mask = document.createElement('div');
  mask.setAttribute('id', 'guip-mask');

  var innerMask = document.createElement('div');
  innerMask.setAttribute('style', `${baseStyle} background-color: rgba(0, 0, 0, 0.45);`);
  mask.append(innerMask);
  var innerText = document.createElement('span');
  innerText.setAttribute('style', `${baseStyle} text-shadow: 1px 1px 10px black; text-align: center; color: white; font-size: 22px; line-height: 100vh;`);
  innerText.textContent = '已冻结';
  mask.append(innerText);
  document.body.appendChild(mask);
  // 禁止直接关闭
  if (BROWSER_IS_FF) {
    window.addEventListener('beforeunload', _beforeUnloadHandler);
  }
}

/**
 * 恢复本页面
 */
function _recoverModule() {
  var mask = document.getElementById('guip-mask');
  if (mask) {
    mask.parentNode.removeChild(mask);
  }
  // 允许直接关闭
  if (BROWSER_IS_FF) {
    window.removeEventListener('beforeunload', _beforeUnloadHandler);
  }
}

/**
 * 处理moduleId与window的映射关系
 * @param {object} param
 */
function _addWindowToMaps({ moduleId, funcCode, childWindow }) {
  if (!childWindow) {
    return;
  }
  if (moduleId) {
    _moduleIdWinMap[moduleId] = childWindow;
    // 删除可能遗留的挂起页面信息
    _suspendModuleIdList = _suspendModuleIdList.filter((value) => value !== moduleId);
  }
  if (funcCode) {
    if (!_funcCodeWinMap[funcCode]) {
      _funcCodeWinMap[funcCode] = [];
    }
    _funcCodeWinMap[funcCode].push(moduleId);
  }
}
/**
 * 判断是否为swf文件
 * @param {String} url
 */
function testIsSwfURL(url) {
  return url && typeof url === 'string' && url.split('?')[0].endsWith('.swf');
}
/**
 * 打开模块的具体实现，允许使用URL直接打开
 * @param {object} param
 * @return {string} moduleId
 */
function openModule2({ url, funcCode, param, moduleId, parentModuleId, checkAuthority = true, callback = null, popup = false, model = false, redirect = false, query }) {
  var inputModuleId = !!moduleId;
  if (!moduleId) {
    if (funcCode) {
      moduleId = `guop_module_${funcCode}`;
    } else {
      moduleId = _genarateModuleID();
    }
  }
  if (!parentModuleId) {
    parentModuleId = (guipModule || {}).moduleId;
  }
  var paramStr = '';
  if (param !== undefined && param !== null && typeof param === 'object') {
    paramStr = JSON.stringify(param);
  } else {
    paramStr = param;
  }
  var moduleData = {
    moduleId,
    parentModuleId,
    // guipToken: getGuipToken(),
    // guipToken2: getGuipToken2(),
    // guwpToken: getGuwpToken(),
    // param: param ? JSON.stringify(param) : null,
    param: paramStr,
  };

  let paramIsLarge = false;
  if (encodeURIComponent(paramStr).length > 4000) {
    moduleData.param = null;
    paramIsLarge = true;
  }

  var fullURL = '';
  if (url) {
    if (testIsSwfURL(url)) {
      throw new Error('目前暂不支持打开SWF页面！');
    } else {
      fullURL = _appendURLWithModuleData(url, moduleData, query);
    }
  } else if (funcCode) {
    if (checkAuthority && globalInfo().noCheckAuthorityFuncCode !== funcCode && globalInfo().funcCodeList && !globalInfo().funcCodeList.includes(funcCode)) {
      if (_userInfo() && _userInfo().userCode) {
        throw new Error(`用户(${_userInfo().userCode})无(${funcCode})交易权限`);
      }
      throw new Error(`用户无(${funcCode})交易权限`);
    }
    var funcVo = _getFuncByCode(funcCode);
    if (funcVo) {
      var { funcUrl, funcName, appId, funcType } = funcVo;
      if (funcType !== '1' && funcType !== '10' && !inputModuleId) {
        moduleId = _genarateModuleID();
        moduleData.moduleId = moduleId;
      }
      if (testIsSwfURL(funcUrl)) {
        throw new Error('目前暂不支持打开SWF页面！');
      }
      var { appRootUrl, appCode } = _getAppById(appId) || {};
      moduleData.funcCode = funcCode;
      moduleData.funcName = funcName;
      moduleData.appCode = appCode;
      if (!(funcUrl && (funcUrl.startsWith('http://') || funcUrl.startsWith('https://')))) {
        if (!appRootUrl) {
          throw new Error(`应用${appCode}的信息不存在！`);
        }
        funcUrl = appRootUrl + funcUrl;
      }
      fullURL = _appendURLWithModuleData(funcUrl, moduleData, query);
    } else {
      throw new Error('该funcCode没找到对应的功能');
    }
  } else {
    throw new Error('url与funcCode不能同时为空');
  }

  // closeAndOpenModule 直接关闭本页面的情况，无法popup及传递大参数 
  if (redirect) {
    window.location.replace(fullURL);
    return;
  }

  // 大参数延迟传递
  _releaseLargeParamByModuleId(moduleId);
  if (paramIsLarge) {
    _moduleIdLargeParamMap[moduleId] = paramStr;
  }

  if (_moduleIdWinMap[moduleId]) {
    var existsWindow = _moduleIdWinMap[moduleId];
    if (!existsWindow || existsWindow.closed) {
      _releaseWindowByModuleId(moduleId);
    } else {
      existsWindow.focus();
      return;
    }
  }

  var feature = popup ? 'width=1024,height=768' : null;
  var childWindow = window.open(fullURL, moduleId, feature);
  _addWindowToMaps({ moduleId, funcCode, childWindow });
  _releaseTransferParamByModuleId(moduleId);
  // model 添加全局遮罩，挂起当前页面
  if (model) {
    _suspendModule();
  }
  if (model || callback) {
    _handleOpenModuleCallback({ model, moduleId, childWindow, callback });
  }

  // 非FF和360企业浏览器环境下，如果页面没有经过任何点击就调用openModule2，需要警告
  if (!BROWSER_IS_FF && !BROWSER_IS_360ENT && !DOM_HAS_CLICKED) {
    console.warn('用户尚未在本页面进行任何点击操作，因此可能由于弹窗被拦截而无法正常打开模块');
  }

  return moduleId;
}

/**
 * 打开模块有callback的后续处理
 * 包括挂起本页面，检测模态页面状态等
 * @param {object} param
 */
function _handleOpenModuleCallback({ model = false, moduleId, childWindow, callback }) {
  const childCloseHandler = (event) => {
    var { method, detail } = event.data || {};
    if (method === 'unloadModule' && detail === moduleId) {
      window.removeEventListener('message', childCloseHandler);
      if (model) {
        _recoverModule();
      }
      if (callback) {
        callback(_moduleIdTransferParamMap[moduleId]);
      }
      _releaseWindowByModuleId(moduleId);
      _releaseTransferParamByModuleId(moduleId);
    }
  };
  window.addEventListener('message', childCloseHandler);
}

/**
 * @deprecated 使用openModule2替代
 * 挂起本页面并打开新模块
 * 在浏览器上，已挂起的页面仅能通过弹出确认框防止用户关闭页面
 * @param {string} funcCode
 * @param {object} param 附加参数
 * @param {string} parentModuleId
 * @param {function} callback 回调函数
 * @param {boolean} checkAuthority
 */
function suspendAndOpenModule(funcCode, param, parentModuleId, callback, checkAuthority = true) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.suspendAndOpenModule(funcCode, param, parentModuleId, callback, checkAuthority);
    return;
  }
  const model = !parentModuleId || parentModuleId === (guipModule || {}).moduleId;
  if (!model) {
    _suspendModuleById(parentModuleId);
  }
  openModule2({ funcCode, param, parentModuleId, checkAuthority, callback, model });
}

/**
 * @deprecated 使用openModule2替代
 * 打开新模块
 * @param {string} funcCode
 * @param {object} param 附加参数
 * @param {string} parentModuleId
 * @param {string} moduleId
 * @param {boolean} checkAuthority
 */
function openModule(funcCode, param, parentModuleId, moduleId, checkAuthority = true) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.openModule(funcCode, param, parentModuleId, moduleId, checkAuthority);
    return;
  }
  openModule2({ funcCode, param, parentModuleId, moduleId, checkAuthority });
}

/**
 * @deprecated 使用openModule2替代
 * 从新窗口打开新模块
 * @param {string} funcCode
 * @param {object} param 附加参数
 * @param {boolean} model 是否模态方式打开窗口
 * @param {string} parentModuleId
 * @param {boolean} checkAuthority
 */
function popUpModule(funcCode, param, model, parentModuleId, checkAuthority = true) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.popUpModule(funcCode, param, true, parentModuleId);
    return;
  }
  openModule2({ funcCode, param, parentModuleId, checkAuthority, model, popup: true });
}

// 是否关闭自己页面本身
var _readyToCloseSelf = false;
/**
 * 关闭模块
 * 在浏览器中，仅能够关闭本页面打开的其他页面
 * @param {string} moduleId
 */
function closeModule(moduleId) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.closeModule(moduleId);
    return;
  }

  // 高版本浏览器禁止自己通过window.close()关掉非脚本打开的页面
  if (!moduleId || moduleId === (guipModule || {}).moduleId) {
    // 处理在有子页面的情况下需要延迟等待'requestGlobalInfo'事件的情况
    if (Object.keys(_moduleIdWinMap).length > 0) {
      _readyToCloseSelf = true;
      setTimeout(() => {
        window.close();
      }, CLOSE_MODULE_TIMEOUT);
    } else {
      window.close();
    }
    return;
  }
  _releaseWindowByModuleId(moduleId);
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * @deprecated 对GUIP页面存在强依赖
 * 根据功能码关闭模块
 * 在浏览器中，仅能够关闭本页面打开的其他页面
 * @param {string} funcCode
 */
function closeModuleByFuncCode(funcCode) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.closeModuleByFuncCode(funcCode);
    return;
  }
  if (!funcCode) {
    return;
  }
  _releaseWindowByFuncCode(funcCode);
  if (funcCode === (guipModule || {}).funcCode) {
    window.close();
  }
}

function _suspendModuleById(moduleId) {
  if (!moduleId) {
    return;
  }
  if (!_windowExistsByModuleId(moduleId)) {
    _releaseWindowByModuleId(moduleId);
    return;
  }

  _moduleIdWinMap[moduleId].postMessage({ method: 'suspendModule' }, '*');
  _suspendModuleIdList.push(moduleId);
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * 挂起模块
 * 在使用浏览器时，只有从GUIP打开的页面才能挂起其他页面，且挂起状态的页面仅能够通过弹出框提示用户即将关闭，不能完全阻止用户关闭页面
 * 因此，在浏览器中，此类场景建议通过iframe嵌入页面的方式实现
 * @param {string} funcCode
 */
function suspendModule(moduleId, param) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.suspendModule(moduleId, param);
    return;
  }

  // TODO param如何处理？
  if (moduleId === (guipModule || {}).moduleId) {
    _suspendModule();
    return;
  }
  _suspendModuleById(moduleId);
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * @deprecated 对GUIP页面存在强依赖
 * 通过功能码挂起模块
 * 在使用浏览器时，只有从GUIP打开的页面才能挂起其他页面，，且挂起状态的页面仅能够通过弹出框提示用户即将关闭，不能完全阻止用户关闭页面
 * 因此，在浏览器中，此类场景建议通过iframe嵌入页面的方式实现
 * @param {string} funcCode
 */
function suspendModuleByFuncCode(funcCode, param) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.suspendModuleByFuncCode(funcCode, param);
  }

  // TODO param如何处理？
  if (funcCode === (guipModule || {}).funcCode) {
    _suspendModule();
  }
  if (!_funcCodeWinMap[funcCode]) {
    _funcCodeWinMap[funcCode] = [];
  }
  for (var moduleId of _funcCodeWinMap[funcCode]) {
    _suspendModuleById(moduleId);
  }
}

function _recoverModuleById(moduleId) {
  if (!moduleId || !_suspendModuleIdList.includes(moduleId)) {
    return;
  }
  if (!_windowExistsByModuleId(moduleId)) {
    _releaseWindowByModuleId(moduleId);
    return;
  }
  _moduleIdWinMap[moduleId].postMessage({ method: 'recoverModule' }, '*');
  _suspendModuleIdList.splice(_suspendModuleIdList.indexOf(moduleId), 1);
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * 恢复模块
 * 在使用浏览器时，只有从GUIP打开的页面才能恢复其他页面，仅能够恢复本页面和本页面打开的其他页面
 * 因此，在浏览器中，此类场景建议通过iframe嵌入页面的方式实现
 * @param {string} funcCode
 */
function recoverModule(moduleId, param) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.recoverModule(moduleId, param);
    return;
  }

  // TODO param如何处理？
  if (moduleId === (guipModule || {}).moduleId) {
    _recoverModule();
    return;
  }
  _recoverModuleById(moduleId);
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * @deprecated 对GUIP页面存在强依赖
 * 通过功能码恢复模块
 * 在浏览器中，仅能够恢复本页面和本页面打开的其他页面
 * 因此，在浏览器中，此类场景建议通过iframe嵌入页面的方式实现
 * @param {string} funcCode
 */
function recoverModuleByFuncCode(funcCode, param) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.recoverModuleByFuncCode(funcCode, param);
    return;
  }

  // TODO param如何处理？
  if (funcCode === (guipModule || {}).funcCode) {
    _recoverModule();
  }
  if (!_funcCodeWinMap[funcCode]) {
    _funcCodeWinMap[funcCode] = [];
  }
  for (var moduleId of _funcCodeWinMap[funcCode]) {
    _recoverModuleById(moduleId);
  }
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * @deprecated 对GUIP页面存在强依赖
 * 统计打开模块数
 * 在浏览器运行时，仅统计本页面关联打开的模块数
 * @param {string} funcCode
 * @param {function} callback
 */
function hasModuleOpened(funcCode, callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.hasModuleOpened(callback, funcCode);
    return;
  }

  var count = 0;
  if (funcCode === (guipModule || {}).funcCode) {
    count++;
  }
  if (_funcCodeWinMap[funcCode]) {
    for (var moduleId of _funcCodeWinMap[funcCode]) {
      if (_windowExistsByModuleId(moduleId)) {
        count++;
      } else {
        _releaseWindowByModuleId(moduleId);
      }
    }
  }
  callback(count);
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * 获取当前选中的模块
 * 在浏览器运行时，无法获取其他页签/window
 * @param {function} callback
 */
function getSelectedModule(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getSelectedModule(callback);
  } else {
    callback(null);
  }
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * 获取当前选中的moduleId
 * 在浏览器运行时，无法获取其他页签/window的状态
 * @param {function} callback
 */
function getSelectedModuleId(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getSelectedModuleId(callback);
  } else {
    // 实际浏览器上无法获取其他页签/window的激活状态
    callback('');
  }
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * 获取模块状态
 * 在浏览器中，仅能够获取本页面和通过本页面挂起的页面状态
 * 因此，在浏览器中，此类场景建议通过iframe嵌入页面的方式实现
 * @param {string} moduleId
 */
function getModuleState(moduleId, callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getModuleState(callback, moduleId);
    return;
  }

  // 当前页面
  if (moduleId === (guipModule || {}).moduleId) {
    if (document.getElementById('guip-mask')) {
      callback('Suspended');
      return;
    } else {
      callback('Activated');
      return;
    }
  }
  // 其他页面
  if (!_windowExistsByModuleId(moduleId)) {
    callback('None');
    _releaseWindowByModuleId(moduleId);
    return;
  }
  if (_suspendModuleIdList.includes(moduleId)) {
    callback('Suspended');
  } else {
    callback('Activated');
  }
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * 获取模块
 * 在浏览器运行时，无法获取其他页签/window
 * @param {function} callback
 */
function getModule(moduleId, callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getModule(callback, moduleId);
  } else {
    callback(null);
  }
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * 关闭二级子模块
 * 在浏览器运行时，页面可自行控制iframe，该接口无效
 * @param {string} moduleId
 */
function closeSubModule(moduleId) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.closeSubModule(moduleId);
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 验证功能码
 * @param {string} funcCode
 * @param {string} callback
 */
function checkFuncAuthority(funcCode, callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.checkFuncAuthority(callback, funcCode);
  } else {
    promise.globalInfo().then((value) => {
      var func = (value.funcCodeList || []).includes(funcCode);
      callback(value.noCheckAuthorityFuncCode === funcCode || func);
    });
  }
}

/**
 * @deprecated 不适用于浏览器的使用场景
 * @deprecated 对GUIP页面存在强依赖
 * 关闭模块并打开新模块
 * 在浏览器中，仅能够关闭本页面打开的其他页面
 * @param {string} moduleId
 */
function closeAndOpenModule(closeModuleId, funcCode, moduleId, param, checkAuthority = true) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.closeAndOpenModule(closeModuleId, funcCode, moduleId, param, checkAuthority);
    return;
  }
  if (!BROWSER_IS_FF && !DOM_HAS_CLICKED && (!closeModuleId || closeModuleId === (guipModule || {}).moduleId)) {
    // 直接关闭本页面，改为修改location模式
    var thisModuleId = (guipModule || {}).moduleId || closeModuleId;
    openModule2({ funcCode, moduleId: thisModuleId, param, checkAuthority, redirect: true });
    return;
  }
  openModule2({ funcCode, moduleId, param, checkAuthority });
  closeModule(closeModuleId);
}

/**
 * 生成功能码
 */
function generateFuncCode(appCode, funcUrl, funcName, alias, openMode, callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.generateFuncCode(callback, appCode, funcUrl, funcName, alias, openMode);
  } else {
    if (!appCode || !funcUrl || !funcName) {
      console.error('generateFuncCode接口必传参数为空');
      callback(null);
      return;
    }
    promise.globalInfo().then((_) => {
      var app = _getAppByCode(appCode);
      if (!app) {
        console.error(`generateFuncCode接口参数appCode:"${appCode}"不存在`);
        callback(null);
        return;
      }
      var funcId = Math.round(99 * Math.pow(10, 10) + (Math.random()) * Math.pow(10, 10));
      var funcCode = `TMP_${appCode}_${funcUrl}**${funcId}${alias ? '|' + alias : ''}`;
      var orgCode = _userInfo().bbosOrgCode;
      var orgName = (_userInfo().linkedOrgName || '').split('/').pop();
      var currentFunc = _getFuncByCode(guipModule.funcCode);
      if (currentFunc) {
        orgCode = currentFunc.orgCode;
        orgName = currentFunc.orgName;
      }
      var funcVO = {
        appId: app.appId,
        funcId,
        funcUrl,
        openMode: openMode ? openMode : '1',
        funcType: '3',
        funcName,
        funcCode,
        alias: alias ? alias : funcCode,
        orgCode,
        orgName,
      };
      _globalInfo.funcCodeList.push(funcCode);
      _globalInfo.funcCodeFullMap[funcCode] = funcVO;
      callback(funcCode);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取本地IP地址
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {function} callback
 */
function getLocalIpAddress(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getLocalIpAddress(callback);
  } else {
    promise.globalInfo().then((value) => {
      callback(value.localIpAddress);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取地区码（境内不支持此接口）
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {function} callback
 */
function getAreaCode(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.getAreaCode(callback);
  } else {
    // TODO 境外如何获取？
    callback('');
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取地区类型
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {function} callback
 */
function getAreaType(callback) {
  if (!!window.guipJsObj && !!window.guipJsObj.getStartupPath) {
    try {
      var startupPath = window.guipJsObj.getStartupPath();
      if (startupPath.toLowerCase().includes('_hk')) {
        callback('guipclient_hkd');
      } else if (startupPath.toLowerCase().includes('_ovs')) {
        callback('guipclient_ovs');
      } else {
        callback('guipclient_chn');
      }
    } catch (error) {
      console.error(error);
      callback('guipclient_chn');
    }
  } else {
    // TODO 暂时只返回cn环境
    callback('guipclient_chn');
  }
}

/**
 * @deprecated 在浏览器上无法使用
 * 建立任务与模块间映射关系
 */
function registerTaskId(taskId, moudleId) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.registerTaskId(taskId, moudleId);
  }
}

/**
 * 是否允许自动锁屏
 * 在浏览器上运行时，对GUBP浏览器扩展存在强依赖
 * @param {boolean} autoLock
 */
function canAutoLock(autoLock) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.canAutoLock(autoLock);
  } else {
    window.postMessage({
      direction: 'page-to-extension',
      message: {
        command: 'setAutoLock', 
        cmdData: autoLock,
      },
    }, '*');
  }
}

/**
 * 如果在页面初始化生命周期中使用 _userInfo()，可能因为没有发出或收到globalInfo消息而取得空消息
 * 建议使用 window.promise._userInfo()
 */
function _userInfo() {
  return globalInfo().userInfo || {};
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取用户ID
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 */
function guipUserId(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.guipUserId(callback);
  } else {
    promise._userInfo().then((value) => {
      callback(value.userId);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取用户柜员号
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 */
function guipUserCode(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.guipUserCode(callback);
  } else {
    promise._userInfo().then((value) => {
      callback(value.userCode);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取用户姓名
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 */
function guipUserName(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.guipUserName(callback);
  } else {
    promise._userInfo().then((value) => {
      callback(value.userName);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取用户登录名
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 */
function guipLoginName(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.guipLoginName(callback);
  } else {
    promise._userInfo().then((value) => {
      callback(value.loginName);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取用户行政机构中文名
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 */
function guipLinkedOrgName(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.guipLinkedOrgName(callback);
  } else {
    promise._userInfo().then((value) => {
      callback(value.linkedOrgName);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取用户行政机构号
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 */
function bbosOrgCodeStr(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.bbosOrgCodeStr(callback);
  } else {
    promise._userInfo().then((value) => {
      callback(value.bbosOrgCode);
    });
  }
}

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取用户行政机构号对应分行号
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 */
function bbosBranchCodeStr(callback) {
  if (guipControl != null && guipControl != undefined) {
    guipControl.bbosBranchCodeStr(callback);
  } else {
    promise._userInfo().then((value) => {
      callback(value.bbosBranchCode);
    });
  }
}

var _userFuncList = [];

/**
 * @deprecated 对GUIP页面存在强依赖
 * 获取用户功能码列表
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {function} callback
 */
function getUserFuncList(callback) {
  if (window.guipControl != null && window.guipControl != undefined) {
    window.guipControl.getUserFuncList(function (data) {
      try {
        var ac = JSON.parse(data);
        callback(ac);
      } catch (e) {
        callback([]);
        console.error('不是有效json格式。', e.message);
        console.info(data);
      }
    });
  } else {
    promise.globalInfo().then((value) => {
      callback(_getUserFuncListSync(value));
    });
  }
}

function _getUserFuncListSync(value) {
  if (_userFuncList && _userFuncList.length > 0) {
    return _userFuncList;
  }
  if (!value.funcCodeList || !value.funcCodeFullMap) {
    return [];
  }
  _userFuncList = value.funcCodeList.map((funcCode) => value.funcCodeFullMap[funcCode]);
  return _userFuncList;
}

/**
 * @deprecated 不适用于浏览器
 * 获取国际化标识
 * @param {function} callback
 */
function getGuipLocalType(callback) {
  if (window.guipControl != null && window.guipControl != undefined) {
    window.guipControl.getGuipLocalType(callback);
  } else {
    callback(navigator.language || navigator.userLanguage);
  }
}

/**
 * 浏览器中ECRM API
 */
function _ecrmAPIForBrowser(methodName, requestDetail) {
  var target;
  if (window.opener) {
    target = window.opener;
  } else if (window.parent !== window){
    target = window.parent;
  }
  if (!target) {
    console.error('没有找到window.opener或window.parent，无法请求任务数据');
    return Promise.resolve([]);
  }

  return new Promise((resolve, _) => {
    var _resolved = false;
    var _callbackListener = (event) => {
      var { command, detail = [] } = event.data;
      if (command !== `response_${methodName}`) {
        return;
      }
      window.removeEventListener('message', _callbackListener);
      resolve(detail);
      _resolved = true;
    };
    window.addEventListener('message', _callbackListener);
    
    target.postMessage({
      command: `request_${methodName}`,
      detail: requestDetail,
    }, '*');

    var timeoutId = setTimeout(() => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      if (_resolved) {
        return;
      }
      window.removeEventListener('message', _callbackListener);
      console.error('使用ECRM API超时，请检查window.opener或window.parent是否为GUBP首页');
      resolve({});
    }, 30000);
  });
}

/**
 * @deprecated 不适用于浏览器
 * @param {function} callback
 */
function queryGuipTodoTask(callback) {
  if (window.guipJsObj != null && window.guipJsObj != undefined) {
    var arr = window.location.href.split('/');
    var arr2 = [arr[0], arr[1], arr[2]];
    var originUrl = arr2.join('/');
    window.guipJsObj.addCrossOriginWhitelistEntry(originUrl);
    if (window.guipControl != null && window.guipControl != undefined) {
      window.guipControl.queryGuipTodoTask(function (path) {
        try {
          getGuipTaskData(path, callback);
        } catch (e) {
          callback('');
          console.error('文件路径异常。', e.message);
          console.info(path);
        }
      });
    }
  } else {
    // callback([]);
    _ecrmAPIForBrowser('queryGuipTodoTask', {}).then((ret) => {
      callback(ret);
    });
  }
}

/**
 * @deprecated 不适用于浏览器
 * @param {string} path
 * @param {function} callback
 */
function getGuipTaskData(path, callback) {
  var url = 'http://guiprecodersave/QUERY_TODO_TASK';
  var xhr = new XMLHttpRequest();
  xhr.open('POST', url, true);
  xhr.setRequestHeader('FilePath', path);
  xhr.send();
  xhr.onload = function () {
    try {
      const result = JSON.parse(xhr.responseText);
      callback(result);
      console.log(result);
    } catch (e) {
      callback([]);
      console.error('不是有效json格式。', e.message);
    }
  };
  xhr.onerror = function (e) {
    console.log(e);
  };
}

/**
 * @deprecated 不适用于浏览器
 * @param {string} appCode
 * @param {string} appTaskId
 * @param {string} taskType
 * @param {function} callback
 */
function queryTodoTaskParameterByTaskIdAndTaskType(
  appCode,
  appTaskId,
  taskType,
  callback
) {
  if (window.guipControl != null && window.guipControl != undefined) {
    window.guipControl.queryTodoTaskParameterByTaskIdAndTaskType(
      function (data) {
        try {
          var jsonObj = JSON.parse(data);
          callback(jsonObj);
        } catch (e) {
          callback([]);

          console.error('不是有效json格式。', e.message);
          console.info(data);
        }
      },
      appCode,
      appTaskId,
      taskType
    );
  } else {
    // callback([]);
    var requestDetail = {
      appCode,
      appTaskId,
      taskType,
    };
    _ecrmAPIForBrowser('queryTodoTaskParameterByTaskIdAndTaskType', requestDetail).then((ret) => {
      callback(ret);
    });
  }
}

// /////////////////////////////////////////////
//	sync
// /////////////////////////////////////////////

var guipJsObj;// 在Cef集成环境中，这个对象会被复写
function showDevTools() {
  if (guipJsObj != null && guipJsObj != undefined) {
    guipJsObj.showDevTools();
  }
}

// /////////////////////////////////////////////
//	guipModule GUIP的模块属性
//  在Cef集成环境中，这个对象会被复写
// /////////////////////////////////////////////
var guipModule;

function _getSearchParams() {
  return new URLSearchParams((window.location.href.split('?')[1] || '').split('#')[0]);
}

var _searchParamNeedDecode = false;
/**
 * 从queryParameter获取guipModule中的属性
 */
function _getGuipModuleData() {
  if (guipModule) {
    return;
  }
  guipModule = {};
  try {
    var params = _getSearchParams();
    var moduleDataStr = params.get('moduleData');
    if (moduleDataStr) {
      if (moduleDataStr.startsWith('%')) {
        _searchParamNeedDecode = true;
        moduleDataStr = decodeURIComponent(moduleDataStr);
      }
      guipModule = JSON.parse(moduleDataStr);
    }
  } catch (error) {
    console.error('转换moduleData为JSON对象失败，请检查', moduleDataStr);
    console.error(error);
  } finally {
    _appendFuncToGuipModule();
  }
}

function _appendFuncToGuipModule() {
  if (!guipModule) {
    guipModule = {};
  }
  guipModule.registerCloseCallBack = (callback) => {
    if (!callback) return;
    var eventType = BROWSER_IS_FF ? 'unload' : 'beforeunload';
    window.addEventListener(eventType, () => {
      callback();
    });
  };
}

!IS_GUIP && _getGuipModuleData();

/**
 * 创建header和footer占位
 */
function _createEmptyHeaderAndFooter(event) {
  if (!guipModule || !document.body) {
    return;
  }
  var params = _getSearchParams();
  var noheader = params.get('noheader');
  if (noheader && (noheader === '1' || noheader.toLowerCase() === 'y' || noheader.toLowerCase() === 'yes' || noheader.toLowerCase() === 'true')) {
    return;
  }

  var extraData = {
    accDate: globalInfo().accDate,
  };
  var oaheader = params.get('oaheader');
  if (oaheader && (oaheader === '1' || oaheader.toLowerCase() === 'y' || oaheader.toLowerCase() === 'yes' || oaheader.toLowerCase() === 'true')) {
    extraData.oaheader = true;
  } else {
    extraData.oaheader = false;
  }
  if (!extraData.oaheader && !guipModule.funcCode) {
    return;
  }
  if (guipModule.funcCode) {
    var funcVo = _getFuncByCode(guipModule.funcCode);
    if (funcVo) {
      extraData.funcCode = funcVo.funcCode;
      extraData.funcName = funcVo.funcName;
      extraData.shortCut = funcVo.shortCut;
      extraData.orgCode = funcVo.orgCode;
      extraData.orgName = funcVo.orgName;
    }
  }
  if (_userInfo()) {
    extraData.userCode = _userInfo().userCode;
    extraData.userName = _userInfo().userName;
    extraData.loginName = _userInfo().loginName;
  }

  var header = document.getElementById('guip-api-header');
  if (!header) {
    header = document.createElement('header');
    header.setAttribute('id', 'guip-api-header');
    header.setAttribute('style', 'display: none;');
    header.setAttribute('extra', JSON.stringify(extraData));
    document.body.appendChild(header);
  } else {
    header.setAttribute('extra', JSON.stringify(extraData));
  }
  var footer = document.getElementById('guip-api-footer');
  if (!document.getElementById('guip-api-footer')) {
    footer = document.createElement('footer');
    footer.setAttribute('id', 'guip-api-footer');
    footer.setAttribute('style', 'display: none;');
    footer.setAttribute('extra', JSON.stringify(extraData));
    document.body.appendChild(footer);
  } else {
    footer.setAttribute('extra', JSON.stringify(extraData));
  }
  // window.postMessage('guipAPIExtraCreated', '*');
  window.postMessage({
    direction: 'page-to-content',
    message: {
      command: 'guipAPIExtraCreated', 
      cmdData: '',
    },
  }, '*');
}

!IS_GUIP && window.addEventListener('load', _createEmptyHeaderAndFooter);

// /////////////////////////////////////////////
//	获取token
// /////////////////////////////////////////////
function _getStandardToken(name) {
  if (!name) {
    return '';
  }

  var params = _getSearchParams();
  if (params.get(name)) {
    if (_searchParamNeedDecode) {
      return decodeURIComponent(params.get(name));
    } else {
      return params.get(name);
    }
  }

  if (guipModule && guipModule[name]) {
    return guipModule[name];
  }

  if (globalInfo() && globalInfo()[name]) {
    return globalInfo()[name];
  }

  return '';
}

function getGuipToken() {
  var standardTokenValue = _getStandardToken('guipToken');
  if (!standardTokenValue && globalInfo() && globalInfo().token) {
    return globalInfo().token;
  }
  return standardTokenValue;
}

function getGuipToken2() {
  return _getStandardToken('guipToken2');
}

function getGuwpToken() {
  return _getStandardToken('guwpToken');
}

// /////////////////////////////////////////////
//	业务系统页面使用以下代码
// /////////////////////////////////////////////
var _globalInfo = {};
var _globalInfoReceived = false;

/**
 * 如果在页面初始化生命周期中使用globalInfo()，可能因为没有发出或收到globalInfo消息而取得空消息
 * 建议使用 window.promise.globalInfo()
 */
function globalInfo() {
  return _globalInfo;
}

/**
 * 接收从GUIP页面发出的GlobalInfo
 */
function _onReceiveMessage(event) {
  var { method, detail, largeParam } = event.data || {};
  if (method === 'globalInfo') {
    setGlobalInfo(detail);
    _setLargeParam(largeParam);
    _createEmptyHeaderAndFooter();
  } else if (method === 'suspendModule') {
    _suspendModule();
  } else if (method === 'recoverModule') {
    _recoverModule();
  } else if (method === 'requestGlobalInfo') {
    if (event.source && event.source.postMessage) {
      var { moduleId } = detail || {};
      promise.globalInfo().then((value) => {
        event.source.postMessage({
          method: 'globalInfo',
          detail: value,
          largeParam: _moduleIdLargeParamMap[moduleId],
        }, '*');
        if (_readyToCloseSelf) {
          window.close();
        }
        _releaseLargeParamByModuleId(moduleId);
      });
    }
  } else if (method === 'unloadModule') {
    var umTimeout = setTimeout(() => {
      if (umTimeout) clearTimeout(umTimeout);
      if (!_windowExistsByModuleId(detail)) _releaseWindowByModuleId(detail);
    }, CLOSE_MODULE_TIMEOUT);
  } else if (method === 'transferParam') {
    var { moduleId, param } = detail || {};
    if (!moduleId) {
      return;
    }
    _moduleIdTransferParamMap[moduleId] = param;
  }
}
!IS_GUIP && window.addEventListener('message', _onReceiveMessage);

/** 发送标准消息 */
function _postStandardMessage(method, detail) {
  if (window.opener) {
    window.opener.postMessage({
      method,
      detail,
    }, '*');
  }
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({
      method,
      detail,
    }, '*');
  }
}

/**
 * 页面unload时发出信号
 */
function _addUnloadListener() {
  var eventType = BROWSER_IS_FF ? 'unload' : 'beforeunload';
  window.addEventListener(eventType, () => {
    _releaseAllWindows();
    _postTransferParamMessage();
    _postUnloadModuleMessage();
  });
}
/** 给父模块传参消息 */
function _postTransferParamMessage() {
  if (!guipModule || !guipModule.moduleId || guipModule.param === null || guipModule.param === undefined) {
    return;
  }
  _postStandardMessage('transferParam', {
    moduleId: guipModule.moduleId,
    param: guipModule.param,
  });
}
/** 卸载模块消息 */
function _postUnloadModuleMessage() {
  if (!guipModule || !guipModule.moduleId) {
    return;
  }
  _postStandardMessage('unloadModule', guipModule.moduleId);
}
!IS_GUIP && _addUnloadListener();
/** 清理所有childWindow等，释放内存 */
function _releaseAllWindows() {
  _funcCodeWinMap = null;
  _funcCodeWinMap = {};
  _suspendModuleIdList = null;
  _suspendModuleIdList = [];
  for (var moduleId in _moduleIdWinMap) {
    _moduleIdWinMap[moduleId] = null;
  }
  _moduleIdWinMap = null;
  _moduleIdWinMap = {};
}

/**
 * 请求GlobalInfo
 */
function _requestGlobalInfo() {
  _postStandardMessage('requestGlobalInfo', {
    moduleId: guipModule.moduleId,
  });
}
!IS_GUIP && _requestGlobalInfo();

// /////////////////////////////////////////////
//	GUIP自身页面需单独设置globalInfo
// /////////////////////////////////////////////
function setGlobalInfo(value) {
  if (!value) {
    return;
  }
  _globalInfo = value;
  _globalInfoReceived = true;
}

/**
 * 设置大参数
 * @param {string} value 
 */
function _setLargeParam(value) {
  if (!value) {
    return;
  }
  if (!guipModule) {
    _getGuipModuleData();
  }
  guipModule.param = value;
}

// 打开indexeddb
!IS_GUIP && _openDB();

// /////////////////////////////////////////////
//	window.guipWordPlugin
//  在Cef集成环境中，这个对象会被复写
// /////////////////////////////////////////////
function docxTextReplaceN(source, target, txtData, tableData) {
  return new Promise((resolve, reject) => {
    if (window.guipWordPlugin != null && window.guipWordPlugin != undefined) {
      window.guipWordPlugin.docxTextReplaceN(
        source,
        target,
        txtData ? JSON.stringify(txtData) : JSON.stringify({}),
        tableData ? JSON.stringify(tableData) : JSON.stringify([]),
        function (data) {
          resolve(JSON.parse(data));
        }
      );
    } else {
      console.error('window.guipWordPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject({ status: '1' }); // 失败
    }
  });
}

function insertPicture(
  templDocPath,
  saveDocPath,
  picPlaceHolder,
  picPath,
  picWidth
) {
  return new Promise((resolve, reject) => {
    if (window.guipWordPlugin != null && window.guipWordPlugin != undefined) {
      window.guipWordPlugin.insertPicture(
        templDocPath,
        saveDocPath,
        picPlaceHolder,
        picPath,
        picWidth,
        function (data) {
          resolve(JSON.parse(data));
        }
      );
    } else {
      console.error('window.guipWordPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject({ status: '1' }); // 失败
    }
  });
}

function convertAdvDocxB(source, target, txtData, tableData) {
  return new Promise((resolve, reject) => {
    if (window.guipWordPlugin != null && window.guipWordPlugin != undefined) {
      window.guipWordPlugin.convertAdvDocxB(
        source,
        target,
        txtData ? JSON.stringify(txtData) : JSON.stringify({}),
        tableData ? JSON.stringify(tableData) : JSON.stringify([]),
        function (data) {
          resolve(JSON.parse(data));
        }
      );
    } else {
      console.error('window.guipWordPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject({ status: '1' }); // 失败
    }
  });
}

// /////////////////////////////////////////////
//	window.guipExcelPlugin
//  在Cef集成环境中，这个对象会被复写
// /////////////////////////////////////////////
function excelReplaceText(source, target, sheetCakeVos) {
  return new Promise((resolve, reject) => {
    if (window.guipExcelPlugin != null && window.guipExcelPlugin != undefined) {
      window.guipExcelPlugin.excelReplaceText(
        source,
        target,
        sheetCakeVos ? JSON.stringify(sheetCakeVos) : JSON.stringify([]),
        function (data) {
          resolve(JSON.parse(data));
        }
      );
    } else {
      console.error('window.guipExcelPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject({ status: '1' }); // 失败
    }
  });
}
// /////////////////////////////////////////////
//	window.guipStampPlugin
//  在Cef集成环境中，这个对象会被复写
// /////////////////////////////////////////////
function STAMP_SQUARE(
  typeName,
  stampType,
  branchName,
  verifyCode,
  date,
  isBread
) {
  return new Promise((resolve, reject) => {
    if (window.guipStampPlugin != null && window.guipStampPlugin != undefined) {
      window.guipStampPlugin.sTAMP_SQUARE(
        typeName,
        stampType,
        branchName,
        verifyCode,
        date,
        isBread,
        (stampPath) => {
          resolve(stampPath);
        }
      );
    } else {
      console.error('window.guipStampPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject('');
    }
  });
}

function STAMP_ELLIPSE(typeName, stampType, branchName, verifyCode, isBread) {
  return new Promise((resolve, reject) => {
    if (window.guipStampPlugin != null && window.guipStampPlugin != undefined) {
      window.guipStampPlugin.sTAMP_ELLIPSE(
        typeName,
        stampType,
        branchName,
        verifyCode,
        isBread,
        (stampPath) => {
          resolve(stampPath);
        }
      );
    } else {
      console.error('window.guipStampPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject(''); // 失败
    }
  });
}

function STAMP_IBM(stampName, stampType, branchName, verifyCode, date) {
  return new Promise((resolve, reject) => {
    if (window.guipStampPlugin != null && window.guipStampPlugin != undefined) {
      window.guipStampPlugin.sTAMP_IBM(
        stampName,
        stampType,
        branchName,
        verifyCode,
        date,
        (stampPath) => {
          resolve(stampPath);
        }
      );
    } else {
      console.error('window.guipStampPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject(''); // 失败
    }
  });
}

function STAMP_IBM_BREAD(stampName, stampType, branchName, verifyCode, date) {
  return new Promise((resolve, reject) => {
    if (window.guipStampPlugin != null && window.guipStampPlugin != undefined) {
      window.guipStampPlugin.sTAMP_IBM_BREAD(
        stampName,
        stampType,
        branchName,
        verifyCode,
        date,
        (stampPath) => {
          resolve(stampPath);
        }
      );
    } else {
      console.error('window.guipStampPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject(''); // 失败
    }
  });
}

function STAMP_BBCS(stampName, businessName, verifyCode) {
  return new Promise((resolve, reject) => {
    if (window.guipStampPlugin != null && window.guipStampPlugin != undefined) {
      window.guipStampPlugin.sTAMP_BBCS(
        stampName,
        businessName,
        verifyCode,
        (stampPath) => {
          resolve(stampPath);
        }
      );
    } else {
      console.error('window.guipStampPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject(''); // 失败
    }
  });
}

function BMWS_COMPANY(
  stampName,
  stampType,
  subsidiaryBankName,
  verifyCode,
  isBread
) {
  return new Promise((resolve, reject) => {
    if (window.guipStampPlugin != null && window.guipStampPlugin != undefined) {
      window.guipStampPlugin.bMWS_COMPANY(
        stampName,
        stampType,
        subsidiaryBankName,
        verifyCode,
        isBread,
        (stampPath) => {
          resolve(stampPath);
        }
      );
    } else {
      console.error('window.guipStampPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject(''); // 失败
    }
  });
}

function BMWS_DEBENTURE(verifyCode) {
  return new Promise((resolve, reject) => {
    if (window.guipStampPlugin != null && window.guipStampPlugin != undefined) {
      window.guipStampPlugin.bMWS_DEBENTURE(verifyCode, (stampPath) => {
        resolve(stampPath);
      });
    } else {
      console.error('window.guipStampPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject(''); // 失败
    }
  });
}

// /////////////////////////////////////////////
//	window.guipPrintPlugin
//  在Cef集成环境中，这个对象会被复写
// /////////////////////////////////////////////
function GuipPrint(url, param) {
  if (window.guipPrintPlugin != null && window.guipPrintPlugin != undefined) {
    window.guipPrintPlugin.guipPrint(url, param);
  } else {
    console.error('window.guipPrintPlugin 内置变量不存在，请求guip 内嵌浏览器中打开');
  }
}

// /////////////////////////////////////////////
//	guip async js object
// /////////////////////////////////////////////
// 文件下载
function DownloadFile(url, savePath) {
  return new Promise((resolve, reject) => {
    if (window.guipAsyncJsObj != null && window.guipAsyncJsObj != undefined) {
      window.guipAsyncJsObj.downloadFile(url, savePath, (result) => {
        resolve(JSON.parse(result));
      });
    } else {
      console.error('window.guipAsyncJsObj 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject({ status: '1', error: '请求guip 内嵌浏览器中打开' }); // 失败
    }
  });
}


// /////////////////////////////////////////////
//	window.guipAccredit GUIP授权
//  在Cef集成环境中，这个对象会被复写
// /////////////////////////////////////////////
function getFingerTypeId(callback) {
  if (window.guipAccredit != null && window.guipAccredit != undefined) {
    window.guipAccredit.getFingerTypeId(function (typeId) {
      callback(typeId);
    });
  } else {
    console.error('window.guipAccredit 内置变量不存在，请在GUIP中使用');
    callback('');
  }
}

function getFingerInfo(callback) {
  if (window.guipAccredit != null && window.guipAccredit != undefined) {
    window.guipAccredit.getFingerInfo(function (data) {
      callback(data);
    });
  } else {
    console.error('window.guipAccredit 内置变量不存在，请在GUIP中使用');
    callback('');
  }
}

// 刷卡
function callReadMag(callback) {
  if (window.guipAccredit != null && window.guipAccredit != undefined) {
    window.guipAccredit.callReadMag(
      function (data) {
        callback(JSON.parse(data)); // data = {trackCode: -666, arr:[]}
      }
    );
  } else {
    console.error('window.guipAccredit 内置变量不存在，请在GUIP中使用');
    callback({ trackCode: -6 });
  }
}

// 关闭刷卡
function closeReadMag() {
  if (window.guipAccredit != null && window.guipAccredit != undefined) {
    window.guipAccredit.closeReadMag();
  } else {
    console.error('window.guipAccredit 内置变量不存在，请在GUIP中使用');
  }
}


// 刷卡超时时间
function getReadMagTimeout() {
  if (window.guipJsObj != null && window.guipJsObj != undefined) {
    return window.guipJsObj.getReadMagTimeout();
  } else {
    console.error('window.guipJsObj 内置变量不存在，请在GUIP中使用');
    return 30;
  }
}

// 加密
function HKAESEncrypt(value) {
  return new Promise((resolve, reject) => {
    if (window.guipAccredit != null && window.guipAccredit != undefined) {
      window.guipAccredit.hKAESEncrypt((encryptStr) => {
        resolve(encryptStr);
      }, value);
    } else {
      console.error('window.guipAsyncJsObj 内置变量不存在，请求guip 内嵌浏览器中打开');
      reject(''); // 失败
    }
  });
}

// 境内授权组件加密
function aesEncrypt(pwd, aesKey, callback) {
  if (window.guipAccredit != null && window.guipAccredit != undefined) {
    window.guipAccredit.aesEncrypt(callback, pwd, aesKey);
  } else {
    console.error('window.guipAsyncJsObj 内置变量不存在，请求guip 内嵌浏览器中打开');
    callback(''); // 失败
  }
}

// /////////////////////////////////////////////
//	部分接口的Promise包装
// /////////////////////////////////////////////

var promise = {
  /** 最多延迟3s获取globalInfo */
  globalInfo: () => new Promise((resolve, _) => {
    if (IS_GUIP) {
      resolve(_globalInfo);
      return;
    }

    if (_globalInfoReceived) {
      resolve(_globalInfo);
      return;
    }
    var count = 0;
    var interval = setInterval(() => {
      if (_globalInfoReceived || count > 30) {
        clearInterval(interval);
        resolve(_globalInfo);
        _globalInfoReceived = true;
      }
      count++;
    }, 100);
  }),
  _userInfo: () => new Promise((resolve, _) => {
    promise.globalInfo().then((value) => {
      resolve(value.userInfo || {});
    });
  }),
  _getFuncByCode: (funcCode) => new Promise((resolve, _) => {
    promise.globalInfo().then((value) => {
      resolve((value.funcCodeFullMap || {})[funcCode]);
    });
  }),
  _getAppByCode: (appCode) => new Promise((resolve, _) => {
    promise.globalInfo().then((value) => {
      resolve((value.appList || []).find((appVo) => appVo.appCode === appCode));
    });
  }),
  _getAppById: (appId) => new Promise((resolve, _) => {
    promise.globalInfo().then((value) => {
      resolve((value.appList || []).find((appVo) => appVo.appId === appId));
    });
  }),
  /**
 * @deprecated 对GUIP页面存在强依赖
 * 根据功能码获取功能名称
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {string} funcCode
 */
  getFuncNameByFuncCode: (funcCode) => new Promise((resolve) => getFuncNameByFuncCode(funcCode, resolve)),
  /**
 * @deprecated 对GUIP页面存在强依赖
 * 根据功能码获取路径
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {string} funcCode
 */
  getUrlByFuncCode: (funcCode) => new Promise((resolve) => getUrlByFuncCode(funcCode, resolve)),
  /**
 * @deprecated 对GUIP页面存在强依赖
 * 根据功能码获取功能名称
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {string} appCode
 */
  getRootUrlByAppCode: (appCode) => new Promise((resolve) => getRootUrlByAppCode(appCode, resolve)),
  /**
 * @deprecated 对GUIP页面存在强依赖
 * 获取本地IP地址
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 */
  getLocalIpAddress: () => new Promise((resolve) => getLocalIpAddress(resolve)),
  getIpBranchCode: () => new Promise((resolve) => getIpBranchCode(resolve)),
  getIpOrgCode: () => new Promise((resolve) => getIpOrgCode(resolve)),
  /**
 * @deprecated 对GUIP页面存在强依赖
 * 获取地区码（境内不支持此接口）
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {function} callback
 */
  getAreaCode: () => new Promise((resolve) => getAreaCode(resolve)),
  /**
 * @deprecated 对GUIP页面存在强依赖
 * 获取地区类型
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 * @param {function} callback
 */
  getAreaType: () => new Promise((resolve) => getAreaType(resolve)),
  /**
 * @deprecated 对GUIP页面存在强依赖
 * 获取移动 E 动终端标识
 * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
 */
  getEMobile: () => new Promise((resolve) => getEMobile(resolve)),
  /**
  * @deprecated 对GUIP页面存在强依赖
  * 港行获取分行会计日期，境内返回accDate
  * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
  */
  getBranchAccDate: () => new Promise((resolve) => getBranchAccDate(resolve)),
  /**
  * @deprecated 对GUIP页面存在强依赖
  * 港行获取子行会计日期，境内返回accDate
  * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
  */
  getSubAccDate: () => new Promise((resolve) => getSubAccDate(resolve)),
  /**
  * @deprecated 对GUIP页面存在强依赖
  * 获取所属模块 id
  */
  getDocumentModuleId: () => new Promise((resolve) => getDocumentModuleId(resolve)),
  /**
  * @deprecated 对GUIP页面存在强依赖
  * 获取用户功能码列表
  * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
  */
  getUserFuncList: () => new Promise((resolve) => getUserFuncList(resolve)),
  /**
  * @deprecated 对GUIP页面存在强依赖
  * 获取用户ID
  * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
  */
  guipUserId: () => new Promise((resolve) => guipUserId(resolve)),
  /**
  * @deprecated 对GUIP页面存在强依赖
  * 获取用户柜员号
  * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
  */
  guipUserCode: () => new Promise((resolve) => guipUserCode(resolve)),
  /**
   * @deprecated 对GUIP页面存在强依赖
   * 获取用户姓名
   * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
   */
  guipUserName: () => new Promise((resolve) => guipUserName(resolve)),

  /**
   * @deprecated 对GUIP页面存在强依赖
   * 获取用户登录名
   * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
   */
  guipLoginName: () => new Promise((resolve) => guipLoginName(resolve)),
  /**
   * @deprecated 对GUIP页面存在强依赖
   * 获取用户行政机构中文名
   * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
   */
  guipLinkedOrgName: () => new Promise((resolve) => guipLinkedOrgName(resolve)),
  /**
   * @deprecated 对GUIP页面存在强依赖
   * 获取用户行政机构号
   * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
   */
  bbosOrgCodeStr: () => new Promise((resolve) => bbosOrgCodeStr(resolve)),
  /**
   * @deprecated 对GUIP页面存在强依赖
   * 获取用户行政机构号对应分行号
   * 在使用浏览器时，只有从GUIP打开的页面才能获取这个值
   */
  bbosBranchCodeStr: () => new Promise((resolve) => bbosBranchCodeStr(resolve)),
  /**
  * @deprecated 不适用于浏览器的使用场景
  * @deprecated 对GUIP页面存在强依赖
  * 统计打开模块数
  * 在浏览器运行时，仅统计本页面关联打开的模块数
  * @param {string} funcCode
  */
  hasModuleOpened: (funcCode) => new Promise((resolve) => hasModuleOpened(funcCode, resolve)),
  /**
  * @deprecated 不适用于浏览器的使用场景
  * 获取模块状态
  * 在浏览器中，仅能够获取本页面和通过本页面挂起的页面状态
  * 因此，在浏览器中，此类场景建议通过iframe嵌入页面的方式实现
  * @param {string} moduleId
  */
  getModuleState: (moduleId) => new Promise((resolve) => getModuleState(moduleId, resolve)),
  /**
  * @deprecated 对GUIP页面存在强依赖
  * 验证功能码
  * @param {string} funcCode
  */
  checkFuncAuthority: (funcCode) => new Promise((resolve) => checkFuncAuthority(funcCode, resolve)),
  /**
  * @deprecated 不适用于浏览器
  * 获取国际化标识
  */
  getGuipLocalType: () => new Promise((resolve) => getGuipLocalType(resolve)),
  /**
    * 生成功能码
    */
  generateFuncCode: (appCode, funcUrl, funcName, alias, openMode) => new Promise((resolve) => generateFuncCode(appCode, funcUrl, funcName, alias, openMode, resolve)),
};

// /////////////////////////////////////////////
//	扩展接口，重度依赖扩展
// /////////////////////////////////////////////
var extension = {
  setZoom: (zoomFactor) => {
    window.postMessage({
      direction: 'page-to-extension',
      message: {
        command: 'setZoom', 
        cmdData: zoomFactor,
      },
    }, '*');
  },
  openModuleByMainPage: (funcCode, param, parentModuleId, moduleId, checkAuthority) => {
    if (IS_GUIP || !Array.from(document.getElementsByTagName('meta')).find((meta) => meta.name === 'gubp-webextension')) {
      openModule(funcCode, param, parentModuleId, moduleId, checkAuthority);
      return;
    }
    console.log('postMessage to extension: callOpenModule2ByMainPage');
    var cmdData = { funcCode, param, parentModuleId, moduleId, checkAuthority };
    if (funcCode && funcCode.startsWith('TMP_')) {
      // 临时功能码
      var funcVo = _getFuncByCode(funcCode);
      if (funcVo) {
        var { funcUrl, appId } = funcVo;
        var { appRootUrl } = _getAppById(appId) || {};
        if (funcUrl) {
          if (funcUrl.startsWith('http://') || funcUrl.startsWith('https://')) {
            cmdData.funcCode = null;
            cmdData.url = funcUrl;
          } else if (appRootUrl) {
            cmdData.funcCode = null;
            cmdData.url = appRootUrl + funcUrl;
          }
        }
      }
    }
    window.postMessage({
      direction: 'page-to-extension',
      message: {
        command: 'callOpenModule2ByMainPage',
        cmdData,
      },
    }, '*');
  },
};
