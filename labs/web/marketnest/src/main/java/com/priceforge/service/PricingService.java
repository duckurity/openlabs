package com.priceforge.service;

import com.priceforge.model.Product;
import org.springframework.expression.Expression;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * Evaluates a user-supplied "pricing formula" column from a bulk-import
 * CSV, e.g. "basePrice * 0.9".
 *
 * THE BUG: instead of a sandboxed math-expression library, this uses
 * Spring's SpelExpressionParser directly against a StandardEvaluationContext,
 * which permits full method invocation, reflection, and type access -
 * i.e. arbitrary Java code execution, not just arithmetic.
 *
 * The BLOCKED_KEYWORDS list below is a deliberately naive attempt at
 * mitigation: a case-insensitive substring blacklist on the two most
 * commonly copy-pasted SpEL RCE building blocks. It does NOT inspect
 * the parsed AST and is trivially defeated by string concatenation or
 * by avoiding those specific words entirely (e.g. via reflection).
 */
@Service
public class PricingService {

    private static final List<String> BLOCKED_KEYWORDS = List.of(
            "runtime",
            "processbuilder"
    );

    private final ExpressionParser parser = new SpelExpressionParser();

    public Object evaluate(String formula, Product product) {
        assertSafe(formula);

        StandardEvaluationContext context = new StandardEvaluationContext(product);
        Expression expression = parser.parseExpression(formula);
        return expression.getValue(context);
    }

    private void assertSafe(String formula) {
        String lowered = formula.toLowerCase();
        for (String keyword : BLOCKED_KEYWORDS) {
            if (lowered.contains(keyword)) {
                throw new SecurityException("Formula rejected: blocked pattern '" + keyword + "'");
            }
        }
    }
}
