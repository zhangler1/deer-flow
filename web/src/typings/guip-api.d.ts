// SPDX-License-Identifier: MIT

/**
 * GuipAPI.xc2.js 全局类型声明
 *
 * 该文件由 GuipAPI.xc2.js 在客户端注入，仅在 GUIP 容器/浏览器环境中可用。
 * SSR 阶段不可访问，使用前需确保 typeof window !== 'undefined'。
 */

/** GUIP 模块信息（从 URL moduleData 解析） */
interface GuipModule {
  moduleId?: string;
  parentModuleId?: string;
  funcCode?: string;
  funcName?: string;
  appCode?: string;
  /** 父模块传入的业务参数（大参数时为 null，需通过 globalInfo 的 largeParam 获取） */
  param?: string | null;
  /** 注册页面关闭回调 */
  registerCloseCallBack?: (callback: () => void) => void;
}

/** 用户信息 */
interface GuipUserInfo {
  userId?: string;
  userCode?: string;
  userName?: string;
  loginName?: string;
  bbosOrgCode?: string;
  bbosBranchCode?: string;
  linkedOrgName?: string;
  [key: string]: unknown;
}

/** 功能码信息 */
interface GuipFuncVo {
  appId?: string;
  funcId?: number;
  funcUrl?: string;
  funcType?: string;
  funcName?: string;
  funcCode?: string;
  openMode?: string;
  alias?: string;
  orgCode?: string;
  orgName?: string;
  shortCut?: string;
}

/** 应用信息 */
interface GuipAppVo {
  appId?: string;
  appCode?: string;
  appRootUrl?: string;
}

/** globalInfo() 返回的全局信息 */
interface GuipGlobalInfo {
  /** guipToken（会话令牌） */
  token?: string;
  guipToken?: string;
  guipToken2?: string;
  guwpToken?: string;
  /** 会计日期 */
  accDate?: string;
  /** 本地 IP 地址 */
  localIpAddress?: string;
  /** 是否免鉴权功能码 */
  noCheckAuthorityFuncCode?: string;
  /** 用户有权限的功能码列表 */
  funcCodeList?: string[];
  /** 功能码详情映射 */
  funcCodeFullMap?: Record<string, GuipFuncVo>;
  /** 应用列表 */
  appList?: GuipAppVo[];
  /** 当前用户信息 */
  userInfo?: GuipUserInfo;
  /** 是否为移动 E 动终端 */
  isEMobile?: boolean;
  [key: string]: unknown;
}

/** openModule2 参数 */
interface OpenModule2Options {
  url?: string;
  funcCode?: string;
  param?: Record<string, unknown> | string | null;
  moduleId?: string;
  parentModuleId?: string;
  checkAuthority?: boolean;
  callback?: ((transferParam: unknown) => void) | null;
  popup?: boolean;
  model?: boolean;
  redirect?: boolean;
  query?: Record<string, string>;
}

/** GuipAPI promise 接口集合 */
interface GuipPromise {
  /** 最多延迟 3s 等待 globalInfo 就绪 */
  globalInfo: () => Promise<GuipGlobalInfo>;
  /** 获取当前用户信息 */
  _userInfo: () => Promise<GuipUserInfo>;
  /** 按功能码获取功能信息 */
  _getFuncByCode: (funcCode: string) => Promise<GuipFuncVo | undefined>;
  /** 按应用编码获取应用信息 */
  _getAppByCode: (appCode: string) => Promise<GuipAppVo | undefined>;
  /** 按应用 ID 获取应用信息 */
  _getAppById: (appId: string) => Promise<GuipAppVo | undefined>;
  /** 获取功能名称 */
  getFuncNameByFuncCode: (funcCode: string) => Promise<string>;
  /** 获取功能 URL */
  getUrlByFuncCode: (funcCode: string) => Promise<string>;
  /** 获取应用根 URL */
  getRootUrlByAppCode: (appCode: string) => Promise<string | null>;
  /** 获取本地 IP */
  getLocalIpAddress: () => Promise<string>;
  /** 获取用户功能码列表 */
  getUserFuncList: () => Promise<GuipFuncVo[]>;
  /** 获取用户 ID */
  guipUserId: () => Promise<string>;
  /** 获取用户柜员号 */
  guipUserCode: () => Promise<string>;
  /** 获取用户姓名 */
  guipUserName: () => Promise<string>;
  /** 获取用户登录名 */
  guipLoginName: () => Promise<string>;
  /** 获取用户行政机构中文名 */
  guipLinkedOrgName: () => Promise<string>;
  /** 获取用户行政机构号 */
  bbosOrgCodeStr: () => Promise<string>;
  /** 获取用户行政机构号对应分行号 */
  bbosBranchCodeStr: () => Promise<string>;
  /** 验证功能码权限 */
  checkFuncAuthority: (funcCode: string) => Promise<boolean>;
  /** 生成功能码 */
  generateFuncCode: (
    appCode: string,
    funcUrl: string,
    funcName: string,
    alias?: string,
    openMode?: string,
  ) => Promise<string>;
}

/** openModule 参数（简化版，兼容旧接口） */
interface OpenModuleOptions {
  funcCode?: string;
  param?: Record<string, unknown> | string | null;
  parentModuleId?: string;
  moduleId?: string;
  checkAuthority?: boolean;
}

declare global {
  /** GUIP 模块信息（从 URL 解析） */
  // eslint-disable-next-line no-var
  var guipModule: GuipModule | undefined;

  /** 同步获取 globalInfo（可能为空，建议用 promise.globalInfo()） */
  // eslint-disable-next-line no-var
  var globalInfo: () => GuipGlobalInfo;

  /** 设置 globalInfo（一般由框架调用） */
  // eslint-disable-next-line no-var
  var setGlobalInfo: (value: GuipGlobalInfo) => void;

  /** 获取 guipToken */
  // eslint-disable-next-line no-var
  var getGuipToken: () => string;

  /** 获取 guipToken2 */
  // eslint-disable-next-line no-var
  var getGuipToken2: () => string;

  /** 获取 guwpToken */
  // eslint-disable-next-line no-var
  var getGuwpToken: () => string;

  /** 打开模块（完整参数） */
  // eslint-disable-next-line no-var
  var openModule2: (options: OpenModule2Options) => string | undefined;

  /** 关闭模块 */
  // eslint-disable-next-line no-var
  var closeModule: (moduleId?: string) => void;

  /** GuipAPI 异步 promise 接口集合 */
  interface Window {
    /** GuipAPI promise 接口 */
    promise: GuipPromise;
    /** GUIP 模块信息 */
    guipModule: GuipModule | undefined;
    /** GUIP 控制对象（仅在 CEF 容器中存在） */
    guipControl?: unknown;
    /** GUIP JS 对象（仅在 CEF 容器中存在） */
    guipJsObj?: unknown;
    /** 同步获取 globalInfo */
    globalInfo: () => GuipGlobalInfo;
    /** 获取 guwpToken */
    getGuwpToken: () => string;
    /** 获取 guipToken */
    getGuipToken: () => string;
    /** 打开模块 */
    openModule2: (options: OpenModule2Options) => string | undefined;
    /** 关闭模块 */
    closeModule: (moduleId?: string) => void;
  }
}

export {};
