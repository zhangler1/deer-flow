#!/usr/bin/env python3
"""
验证脚本:测试选择"对公营销报告"风格后,深度研究节点会加载正确的提示词

运行方式:
    cd /home/lwh/project/deer-flow
    .venv/bin/python tests/verify_business_marketing_prompts.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prompts.template import _get_prompt_env, apply_prompt_template
from src.config.configuration import Configuration


def main():
    print('=' * 80)
    print('DeerFlow 对公营销报告风格 - 提示词加载验证测试')
    print('=' * 80)

    # 测试1: 环境选择
    print('\n测试 1: 提示词环境选择')
    print('-' * 80)

    env_default = _get_prompt_env(None)
    print(f'✓ 默认风格 (None):')
    print(f'  搜索路径: {env_default.loader.searchpath}')

    env_academic = _get_prompt_env('academic')
    print(f'\n✓ 学术风格:')
    print(f'  搜索路径: {env_academic.loader.searchpath}')

    env_business = _get_prompt_env('business_marketing')
    print(f'\n✓ 对公营销报告风格:')
    print(f'  搜索路径: {env_business.loader.searchpath}')

    # 验证路径是否正确
    expected_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../src/prompts/business_marketing"
    )
    actual_path = env_business.loader.searchpath[0]
    expected_path = os.path.normpath(expected_path)
    actual_path = os.path.normpath(actual_path)

    if actual_path == expected_path:
        print(f'\n✅ 对公营销报告路径验证成功!')
        print(f'   期望路径: {expected_path}')
        print(f'   实际路径: {actual_path}')
    else:
        print(f'\n❌ 路径验证失败!')
        print(f'   期望路径: {expected_path}')
        print(f'   实际路径: {actual_path}')
        return 1

    # 测试2: 文件存在性
    print('\n' + '=' * 80)
    print('测试 2: 提示词文件存在性检查')
    print('-' * 80)

    required_files = [
        'coordinator.md',
        'planner.md',
        'reporter.md',
        'researcher.md'
    ]

    base_dir = os.path.dirname(os.path.abspath(__file__))
    business_marketing_dir = os.path.join(
        base_dir,
        '../src/prompts/business_marketing'
    )
    business_marketing_dir = os.path.normpath(business_marketing_dir)

    all_exist = True
    for filename in required_files:
        filepath = os.path.join(business_marketing_dir, filename)
        filepath = os.path.normpath(filepath)
        exists = os.path.exists(filepath)

        status = '✅' if exists else '❌'
        print(f'{status} {filename}')

        if not exists:
            all_exist = False
            print(f'   路径: {filepath}')
        else:
            # 显示文件大小
            size = os.path.getsize(filepath)
            print(f'   大小: {size} bytes')

    if not all_exist:
        print(f'\n❌ 部分提示词文件缺失!')
        return 1

    print(f'\n✅ 所有必需的提示词文件都存在于: {business_marketing_dir}')

    # 测试3: 加载提示词内容
    print('\n' + '=' * 80)
    print('测试 3: 加载不同风格的提示词内容')
    print('-' * 80)

    test_nodes = ['coordinator', 'planner', 'reporter', 'researcher']

    print('\n测试默认风格提示词:')
    print('-' * 80)
    for node in test_nodes:
        try:
            env = _get_prompt_env(None)
            template = env.get_template(f'{node}.md')
            content = template.render(CURRENT_TIME='2025-01-16')
            print(f'✅ {node}.md - 成功加载 ({len(content)} 字符)')
        except Exception as e:
            print(f'❌ {node}.md - 加载失败: {e}')
            return 1

    print('\n测试对公营销报告风格提示词:')
    print('-' * 80)
    for node in test_nodes:
        try:
            env = _get_prompt_env('business_marketing')
            template = env.get_template(f'{node}.md')
            content = template.render(CURRENT_TIME='2025-01-16')
            print(f'✅ {node}.md - 成功加载 ({len(content)} 字符)')
        except Exception as e:
            print(f'❌ {node}.md - 加载失败: {e}')
            return 1

    print('\n✅ 所有节点的提示词都可以成功加载!')

    # 测试4: apply_prompt_template 集成
    print('\n' + '=' * 80)
    print('测试 4: apply_prompt_template 函数集成测试')
    print('-' * 80)

    test_state = {
        'messages': [{'role': 'user', 'content': '测试消息'}],
        'research_topic': '测试主题'
    }

    test_cases = [
        ('academic', '学术风格'),
        ('business_marketing', '对公营销报告风格'),
        ('news', '新闻风格'),
    ]

    for style_value, style_name in test_cases:
        try:
            config = Configuration()
            config.report_style = style_value

            result = apply_prompt_template(
                'researcher',
                test_state,
                config
            )

            if isinstance(result, list) and len(result) > 0:
                first_message = result[0]
                if first_message.get('role') == 'system':
                    print(f'✅ {style_name} ({style_value}):')
                    print(f'   系统提示词长度: {len(first_message["content"])} 字符')
                    if 'CURRENT_TIME' in first_message['content'] or '2025' in first_message['content']:
                        print(f'   ✓ 模板变量已正确渲染')
                else:
                    print(f'❌ {style_name}: 返回格式错误')
                    return 1
            else:
                print(f'❌ {style_name}: 返回结果为空')
                return 1

        except Exception as e:
            print(f'❌ {style_name} ({style_value}): 加载失败 - {e}')
            return 1

    print('\n✅ apply_prompt_template 函数正确处理所有报告风格!')

    # 测试5: 内容差异化
    print('\n' + '=' * 80)
    print('测试 5: 验证不同风格的提示词内容差异化')
    print('-' * 80)

    env_default = _get_prompt_env('academic')
    template_default = env_default.get_template('researcher.md')
    content_default = template_default.render(CURRENT_TIME='2025-01-16')

    env_business = _get_prompt_env('business_marketing')
    template_business = env_business.get_template('researcher.md')
    content_business = template_business.render(CURRENT_TIME='2025-01-16')

    if content_default == content_business:
        print('❌ 提示词内容完全相同 - 这说明没有使用自定义的提示词!')
        print('   提示: 请编辑 src/prompts/business_marketing/ 目录下的文件')
        return 1
    else:
        print('✅ 提示词内容存在差异!')
        print(f'   默认风格长度: {len(content_default)} 字符')
        print(f'   对公营销报告风格长度: {len(content_business)} 字符')
        print(f'   差异: {abs(len(content_default) - len(content_business))} 字符')

        print('\n默认风格预览 (前100字符):')
        print(f'   {content_default[:100]}...')
        print('\n对公营销报告风格预览 (前100字符):')
        print(f'   {content_business[:100]}...')

    # 总结
    print('\n' + '=' * 80)
    print('测试总结')
    print('=' * 80)
    print('✅ 通过 - 提示词环境选择')
    print('✅ 通过 - 提示词文件存在性')
    print('✅ 通过 - 加载提示词内容')
    print('✅ 通过 - apply_prompt_template 集成')
    print('✅ 通过 - 提示词内容差异化')
    print('\n总计: 5/5 测试通过')

    print('\n🎉 所有测试通过! 对公营销报告风格提示词加载功能正常!')
    print('\n下一步:')
    print('  1. 编辑 src/prompts/business_marketing/ 目录下的 .md 文件')
    print('  2. 根据对公营销报告的需求自定义提示词内容')
    print('  3. 在前端选择 "对公营销报告" 风格进行测试')
    print('=' * 80)

    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
