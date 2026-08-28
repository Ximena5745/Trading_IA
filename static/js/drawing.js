// Drawing tools manager for TRADER·IA dashboard
// Phase 1: Implements 8 drawing tools, undo/redo, persistence hooks
// Author: Copilot (2026)

class DrawingManager {
    constructor(canvas, chartId) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.chartId = chartId;
        this.activeTool = null;
        this.drawings = [];
        this.undoStack = [];
        this.redoStack = [];
        this.isDrawing = false;
        this.currentDrawing = null;
        this.initEvents();
    }
    setTool(tool) {
        this.activeTool = tool;
    }
    addDrawing(drawing) {
        this.drawings.push(drawing);
        this.undoStack.push({action: 'add', drawing});
        this.redoStack = [];
        this.redraw();
    }
    undo() {
        if (this.undoStack.length === 0) return;
        const last = this.undoStack.pop();
        if (last.action === 'add') {
            this.drawings.pop();
            this.redoStack.push(last);
        }
        // ... handle other actions
        this.redraw();
    }
    redo() {
        if (this.redoStack.length === 0) return;
        const last = this.redoStack.pop();
        if (last.action === 'add') {
            this.drawings.push(last.drawing);
            this.undoStack.push(last);
        }
        // ... handle other actions
        this.redraw();
    }
    clear() {
        this.drawings = [];
        this.undoStack = [];
        this.redoStack = [];
        this.redraw();
    }
    redraw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        for (const d of this.drawings) {
            d.draw(this.ctx);
        }
    }
    initEvents() {
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
    }
    onMouseDown(e) {
        if (!this.activeTool) return;
        this.isDrawing = true;
        this.currentDrawing = this.activeTool.start(e, this.ctx);
    }
    onMouseMove(e) {
        if (!this.isDrawing || !this.currentDrawing) return;
        this.activeTool.move(e, this.currentDrawing, this.ctx);
        this.redraw();
        this.currentDrawing.draw(this.ctx);
    }
    onMouseUp(e) {
        if (!this.isDrawing || !this.currentDrawing) return;
        this.activeTool.end(e, this.currentDrawing, this.ctx);
        this.addDrawing(this.currentDrawing);
        this.isDrawing = false;
        this.currentDrawing = null;
    }
    // ... persistence hooks (save/load)
}

// Example tool: Line
class LineTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'line', x1: p.x, y1: p.y, x2: p.x, y2: p.y, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#00f';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.lineTo(this.x2, this.y2);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Rectangle Tool
class RectangleTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'rect', x1: p.x, y1: p.y, x2: p.x, y2: p.y, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#f5a623';
        ctx.lineWidth = 2;
        ctx.strokeRect(this.x1, this.y1, this.x2-this.x1, this.y2-this.y1);
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Triangle Tool
class TriangleTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'triangle', x1: p.x, y1: p.y, x2: p.x, y2: p.y, x3: p.x, y3: p.y, step: 1, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        if(drawing.step===1){ drawing.x2 = p.x; drawing.y2 = p.y; }
        else if(drawing.step===2){ drawing.x3 = p.x; drawing.y3 = p.y; }
    }
    end(e, drawing, ctx) {
        if(drawing.step===1){ drawing.step=2; } else { drawing.step=3; }
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#00d084';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.lineTo(this.x2, this.y2);
        ctx.lineTo(this.x3, this.y3);
        ctx.closePath();
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Text Tool
class TextTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'text', x: p.x, y: p.y, text: 'Texto', draw: this.draw};
    }
    move(e, drawing, ctx) {
        // No-op for text
    }
    end(e, drawing, ctx) {
        // Prompt for text
        const t = prompt('Texto:', drawing.text||'');
        if(t!==null) drawing.text = t;
    }
    draw(ctx) {
        ctx.save();
        ctx.font = '16px JetBrains Mono, monospace';
        ctx.fillStyle = '#fff';
        ctx.fillText(this.text, this.x, this.y);
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Parallel Line Tool
class ParallelLineTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'parallel', x1: p.x, y1: p.y, x2: p.x, y2: p.y, offset: 20, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#ff4757';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.lineTo(this.x2, this.y2);
        ctx.moveTo(this.x1, this.y1+this.offset);
        ctx.lineTo(this.x2, this.y2+this.offset);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Curved Line Tool
class CurvedLineTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'curve', x1: p.x, y1: p.y, x2: p.x, y2: p.y, cx: p.x+30, cy: p.y-30, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
        drawing.cx = (drawing.x1 + drawing.x2)/2;
        drawing.cy = drawing.y1 - 40;
    }
    end(e, drawing, ctx) {
        // No-op
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#a78bfa';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.quadraticCurveTo(this.cx, this.cy, this.x2, this.y2);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Ray Tool
class RayTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'ray', x1: p.x, y1: p.y, x2: p.x, y2: p.y, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        // No-op
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#00d9ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        // Extiende la línea más allá del canvas
        const dx = this.x2 - this.x1;
        const dy = this.y2 - this.y1;
        const len = Math.sqrt(dx*dx+dy*dy);
        const scale = 1000/len;
        ctx.lineTo(this.x1 + dx*scale, this.y1 + dy*scale);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Extended Line Tool
class ExtendedLineTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'extend', x1: p.x, y1: p.y, x2: p.x, y2: p.y, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        // No-op
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        // Extiende la línea en ambas direcciones
        const dx = this.x2 - this.x1;
        const dy = this.y2 - this.y1;
        const len = Math.sqrt(dx*dx+dy*dy);
        const scale = 1000/len;
        ctx.beginPath();
        ctx.moveTo(this.x1 - dx*scale, this.y1 - dy*scale);
        ctx.lineTo(this.x2 + dx*scale, this.y2 + dy*scale);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Fibonacci Retracement Tool
// Drag from swing point A (0%) to swing point B (100%); horizontal levels are
// drawn at the standard retracement ratios between the two prices.
class FibonacciTool {
    constructor() {
        this.levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
    }
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'fib', x1: p.x, y1: p.y, x2: p.x, y2: p.y, levels: this.levels, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    draw(ctx) {
        ctx.save();
        ctx.font = '10px JetBrains Mono, monospace';
        const xL = Math.min(this.x1, this.x2);
        const xR = Math.max(this.x1, this.x2);
        for (const lvl of (this.levels || [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1])) {
            const y = this.y1 + (this.y2 - this.y1) * lvl;
            ctx.strokeStyle = 'rgba(245,166,35,0.55)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(xL, y);
            ctx.lineTo(xR, y);
            ctx.stroke();
            ctx.fillStyle = '#f5a623';
            ctx.fillText((lvl * 100).toFixed(1) + '%', xR + 4, y + 3);
        }
        // Vertical anchors
        ctx.strokeStyle = 'rgba(245,166,35,0.25)';
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.lineTo(this.x1, this.y2);
        ctx.moveTo(this.x2, this.y1);
        ctx.lineTo(this.x2, this.y2);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Elliott Wave Tool
// Drag from the start of the move (0) to the projected end (5). A canonical
// 5-wave impulse zigzag is generated between the two points with the usual
// proportions (wave 3 the longest, 2 & 4 partial retracements) and labelled
// 0-1-2-3-4-5. It's a template to nudge, not a strict pivot editor.
class ElliottWaveTool {
    // Fraction of the 0->5 vector reached at each pivot, plus a perpendicular
    // wobble so 2 and 4 read as retracements rather than a straight line.
    static PIVOTS = [
        {t: 0.00, perp: 0.00},
        {t: 0.28, perp: 0.10},
        {t: 0.16, perp: -0.06},
        {t: 0.72, perp: 0.16},
        {t: 0.56, perp: -0.04},
        {t: 1.00, perp: 0.00},
    ];
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'elliott', x1: p.x, y1: p.y, x2: p.x, y2: p.y, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    draw(ctx) {
        const dx = this.x2 - this.x1;
        const dy = this.y2 - this.y1;
        const px = -dy, py = dx; // perpendicular vector
        const pts = ElliottWaveTool.PIVOTS.map(k => ({
            x: this.x1 + dx * k.t + px * k.perp,
            y: this.y1 + dy * k.t + py * k.perp,
        }));
        ctx.save();
        ctx.strokeStyle = '#8b5cf6';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
        ctx.stroke();
        ctx.font = 'bold 12px JetBrains Mono, monospace';
        ctx.fillStyle = '#c4b5fd';
        pts.forEach((pt, i) => ctx.fillText(String(i), pt.x + 5, pt.y - 5));
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

window.DrawingManager = DrawingManager;
window.FibonacciTool = FibonacciTool;
window.ElliottWaveTool = ElliottWaveTool;
window.LineTool = LineTool;
window.RectangleTool = RectangleTool;
window.TriangleTool = TriangleTool;
window.TextTool = TextTool;
window.ParallelLineTool = ParallelLineTool;
window.CurvedLineTool = CurvedLineTool;
window.RayTool = RayTool;
window.ExtendedLineTool = ExtendedLineTool;
