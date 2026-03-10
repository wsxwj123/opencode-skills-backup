# App Factory Skill

<skill>
  <name>app-factory</name>
  <description>零配置跨平台应用工厂。将自然语言需求一键转换为 Windows (.exe) 或 macOS (.app) 可执行文件。自动处理环境准备、代码编写、UI 设计和打包发布全流程。</description>
  <usage>
    当用户需要制作独立运行的桌面软件时使用。
    触发示例：
    - "写一个番茄钟并打包成 exe"
    - "制作一个桌面版的汇率转换器"
    - "把这个网页工具做成 macOS app"
  </usage>
  <workflow>
    <step>
      <name>1. 初始化与环境检查</name>
      <action>
        *   确认 `web-to-app` skill 是否可用（它是打包核心）。
        *   在当前目录下创建一个临时构建工作区，例如 `build_workspace_{timestamp}`，确保不污染用户现有项目。
        *   告知用户："正在初始化应用工厂，准备构建环境..."
      </action>
    </step>
    <step>
      <name>2. 智能开发 (AI Coding)</name>
      <action>
        *   根据用户需求，设计应用架构。
        *   如果涉及复杂交互或美观界面，优先调用 `@designer` 或 `frontend-design` 生成高质量的 HTML/CSS/JS 代码。
        *   **强制要求**：代码必须是**单文件 HTML** (Single File Component) 形式，或者确保所有资源引用使用相对路径，以便本地运行。
        *   将代码写入工作区的 `index.html`。
      </action>
    </step>
    <step>
      <name>3. 快速验证</name>
      <action>
        *   提供 `index.html` 的绝对路径给用户。
        *   询问用户："应用代码已生成，请在浏览器打开上述路径查看预览。如果满意，请回复'打包'；如果需要修改，请直接告诉我调整意见。"
      </action>
    </step>
    <step>
      <name>4. 自动化打包</name>
      <action>
        *   当用户确认满意后，立即调用 `web-to-app` skill。
        *   **输入参数**：
            *   URL/Path: 指向步骤 2 生成的 `index.html` 路径。
            *   Name: 根据应用功能起一个简洁的英文名（如 `PomodoroTimer`）。
            *   Platform: 自动识别当前系统 (Windows/macOS) 或遵循用户指定。
        *   **执行**：监控打包过程，处理可能出现的依赖问题。
      </action>
    </step>
    <step>
      <name>5. 交付与清理</name>
      <action>
        *   打包成功后，向用户展示最终 `.exe` 或 `.app` 文件的确切位置。
        *   询问用户是否保留源码，如果不需要，自动清理临时构建工作区。
        *   结束语："您的应用已就绪！"
      </action>
    </step>
  </workflow>
</skill>
