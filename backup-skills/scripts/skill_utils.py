#!/usr/bin/env python3
"""
技能文件工具
"""

import os
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime

class SkillUtils:
    """技能工具类"""
    
    def __init__(self, skills_dir):
        self.skills_dir = Path(skills_dir)
    
    def get_skill_list(self):
        """获取技能列表"""
        skills = []
        
        if not self.skills_dir.exists():
            return skills
        
        for item in self.skills_dir.iterdir():
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    skills.append({
                        "name": item.name,
                        "path": str(item),
                        "has_skill_md": True,
                        "size": self.get_directory_size(item)
                    })
                else:
                    skills.append({
                        "name": item.name,
                        "path": str(item),
                        "has_skill_md": False,
                        "size": self.get_directory_size(item)
                    })
        
        return sorted(skills, key=lambda x: x["name"])
    
    def get_directory_size(self, directory):
        """获取目录大小（字节）"""
        total_size = 0
        for path in directory.rglob('*'):
            if path.is_file():
                total_size += path.stat().st_size
        return total_size
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def get_file_hash(self, file_path):
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None
    
    def get_directory_hash(self, directory):
        """计算目录哈希值（基于所有文件）"""
        hash_md5 = hashlib.md5()
        
        for root, dirs, files in os.walk(directory):
            # 按字母顺序排序以确保一致性
            files.sort()
            dirs.sort()
            
            for file in files:
                file_path = Path(root) / file
                file_hash = self.get_file_hash(file_path)
                if file_hash:
                    # 包含相对路径和哈希值
                    rel_path = str(file_path.relative_to(directory))
                    hash_md5.update(rel_path.encode())
                    hash_md5.update(file_hash.encode())
        
        return hash_md5.hexdigest()
    
    def compare_directories(self, dir1, dir2):
        """比较两个目录的差异"""
        dir1 = Path(dir1)
        dir2 = Path(dir2)
        
        differences = {
            "added": [],
            "removed": [],
            "modified": [],
            "unchanged": []
        }
        
        # 获取两个目录的所有文件
        files1 = {}
        files2 = {}
        
        for root, dirs, files in os.walk(dir1):
            for file in files:
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(dir1))
                files1[rel_path] = self.get_file_hash(file_path)
        
        for root, dirs, files in os.walk(dir2):
            for file in files:
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(dir2))
                files2[rel_path] = self.get_file_hash(file_path)
        
        # 比较文件
        all_files = set(files1.keys()) | set(files2.keys())
        
        for file in all_files:
            if file in files1 and file not in files2:
                differences["removed"].append(file)
            elif file not in files1 and file in files2:
                differences["added"].append(file)
            elif files1[file] != files2[file]:
                differences["modified"].append(file)
            else:
                differences["unchanged"].append(file)
        
        return differences
    
    def create_backup_report(self, backup_dir, original_dir):
        """创建备份报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "backup_directory": str(backup_dir),
            "original_directory": str(original_dir),
            "comparison": self.compare_directories(original_dir, backup_dir),
            "statistics": {}
        }
        
        # 统计信息
        diff = report["comparison"]
        report["statistics"] = {
            "total_files": len(diff["added"]) + len(diff["removed"]) + 
                          len(diff["modified"]) + len(diff["unchanged"]),
            "added_files": len(diff["added"]),
            "removed_files": len(diff["removed"]),
            "modified_files": len(diff["modified"]),
            "unchanged_files": len(diff["unchanged"])
        }
        
        return report
    
    def save_report(self, report, output_file):
        """保存报告到文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def load_report(self, report_file):
        """从文件加载报告"""
        with open(report_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def filter_skills(self, skills_list, keyword=None, has_skill_md=None):
        """过滤技能列表"""
        filtered = skills_list.copy()
        
        if keyword:
            filtered = [s for s in filtered if keyword.lower() in s["name"].lower()]
        
        if has_skill_md is not None:
            filtered = [s for s in filtered if s["has_skill_md"] == has_skill_md]
        
        return filtered
    
    def get_skill_info(self, skill_name):
        """获取技能详细信息"""
        skill_path = self.skills_dir / skill_name
        
        if not skill_path.exists() or not skill_path.is_dir():
            return None
        
        info = {
            "name": skill_name,
            "path": str(skill_path),
            "exists": True,
            "is_directory": skill_path.is_dir(),
            "files": [],
            "size": self.get_directory_size(skill_path),
            "formatted_size": self.format_size(self.get_directory_size(skill_path)),
            "last_modified": datetime.fromtimestamp(skill_path.stat().st_mtime).isoformat()
        }
        
        # 获取文件列表
        for root, dirs, files in os.walk(skill_path):
            for file in files:
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(skill_path))
                
                file_info = {
                    "path": rel_path,
                    "size": file_path.stat().st_size,
                    "formatted_size": self.format_size(file_path.stat().st_size),
                    "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "hash": self.get_file_hash(file_path)
                }
                
                info["files"].append(file_info)
        
        # 检查是否有 SKILL.md
        skill_md = skill_path / "SKILL.md"
        info["has_skill_md"] = skill_md.exists()
        
        if info["has_skill_md"]:
            info["skill_md_size"] = skill_md.stat().st_size
            info["skill_md_hash"] = self.get_file_hash(skill_md)
        
        return info
    
    def create_skill_summary(self):
        """创建技能摘要"""
        skills = self.get_skill_list()
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "skills_directory": str(self.skills_dir),
            "total_skills": len(skills),
            "skills_with_md": len([s for s in skills if s["has_skill_md"]]),
            "skills_without_md": len([s for s in skills if not s["has_skill_md"]]),
            "total_size": sum(s["size"] for s in skills),
            "skills": []
        }
        
        for skill in skills:
            skill_info = {
                "name": skill["name"],
                "has_skill_md": skill["has_skill_md"],
                "size": skill["size"],
                "formatted_size": self.format_size(skill["size"])
            }
            summary["skills"].append(skill_info)
        
        summary["formatted_total_size"] = self.format_size(summary["total_size"])
        
        return summary
    
    def backup_skill(self, skill_name, backup_dir):
        """备份单个技能"""
        skill_path = self.skills_dir / skill_name
        target_dir = Path(backup_dir) / skill_name
        
        if not skill_path.exists():
            return False, f"技能不存在: {skill_name}"
        
        try:
            # 如果目标目录存在，先删除
            if target_dir.exists():
                shutil.rmtree(target_dir)
            
            # 复制目录
            shutil.copytree(skill_path, target_dir)
            return True, f"成功备份技能: {skill_name}"
        except Exception as e:
            return False, f"备份失败: {str(e)}"
    
    def restore_skill(self, backup_path, skill_name=None):
        """从备份恢复技能"""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            return False, f"备份不存在: {backup_path}"
        
        # 如果没有指定技能名，使用备份目录名
        if skill_name is None:
            skill_name = backup_path.name
        
        target_dir = self.skills_dir / skill_name
        
        try:
            # 如果目标目录存在，先备份
            if target_dir.exists():
                backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_backup = target_dir.parent / f"{target_dir.name}.backup_{backup_time}"
                shutil.move(target_dir, backup_backup)
            
            # 恢复
            if backup_path.is_file():
                shutil.copy2(backup_path, target_dir)
            else:
                shutil.copytree(backup_path, target_dir)
            
            return True, f"成功恢复技能: {skill_name}"
        except Exception as e:
            return False, f"恢复失败: {str(e)}"
    
    def validate_skill_structure(self, skill_name):
        """验证技能结构"""
        skill_path = self.skills_dir / skill_name
        
        if not skill_path.exists():
            return False, ["技能目录不存在"]
        
        errors = []
        warnings = []
        
        # 检查 SKILL.md
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            errors.append("缺少 SKILL.md 文件")
        else:
            # 检查 SKILL.md 内容
            try:
                content = skill_md.read_text(encoding='utf-8')
                if not content.strip():
                    warnings.append("SKILL.md 文件为空")
                
                # 检查 YAML frontmatter
                if not content.startswith('---'):
                    warnings.append("SKILL.md 可能缺少 YAML frontmatter")
            except Exception as e:
                errors.append(f"无法读取 SKILL.md: {str(e)}")
        
        # 检查目录结构
        for item in skill_path.iterdir():
            if item.is_dir():
                if item.name not in ['scripts', 'references', 'assets']:
                    warnings.append(f"非标准目录: {item.name}")
        
        if errors:
            return False, errors + warnings
        elif warnings:
            return True, warnings
        else:
            return True, ["技能结构完整"]